from __future__ import annotations

from typing import Iterable, Sequence

import click
from pymongo import UpdateOne

from pg2mongo import collections as cols
from pg2mongo.builders.income_statement_build import build_income_statement_doc
from pg2mongo.utils import pg_row_to_dict


INCOME_STATEMENT_SELECT_SQL = """
SELECT ist.id,
       ist.stmt_date,
       ist.supervisor_id,
       ist.container_id,
       ist.delivery_id,
       ist.branch_id,
       ist.rate,
       ist.currency,
       ist.time_created,
       ist.time_modified,
       ist.state,
       ist.balance_day,
       ist.balance_previous_day,
       ist.income_type,
       ist.invoice_total,
       ist.receipt_total,
       ist.other_incomes,
       ist.expenses,
       ist.account_receivable,
       ist.loans,
       ist.discounts,
       ist.accounts_transfer,
       ist.commission,
       b.code AS branch_code,
       b.name AS branch_name,
       e.name AS supervisor_name,
       c.designation AS container_designation,
       d.delivery_number AS delivery_number
FROM income_statement ist
LEFT JOIN branch b ON b.id = ist.branch_id
LEFT JOIN employee e ON e.id = ist.supervisor_id
LEFT JOIN container c ON c.id = ist.container_id
LEFT JOIN delivery d ON d.id = ist.delivery_id
"""

INCOME_STATEMENT_BY_WINDOW_SQL = (
    INCOME_STATEMENT_SELECT_SQL
    + """
WHERE ist.time_modified BETWEEN SYMMETRIC %s AND %s
ORDER BY ist.id
"""
)

INCOME_STATEMENT_BY_IDS_SQL = (
    INCOME_STATEMENT_SELECT_SQL
    + """
WHERE ist.id = ANY(%s)
ORDER BY ist.id
"""
)

INCOME_STATEMENT_COUNT_SQL = """
SELECT COUNT(*)::bigint AS cnt
FROM income_statement ist
WHERE ist.time_modified BETWEEN SYMMETRIC %s AND %s
"""


def _fetch_rows(pg_conn, sql: str, params: tuple | list) -> list[dict]:
    rows: list[dict] = []
    with pg_conn.cursor() as cur:
        cur.execute(sql, params)
        for row in cur:
            rows.append(pg_row_to_dict(row))
    return rows


def upsert_income_statements(
    pg_conn,
    mongo_client,
    mongo_db_name: str,
    rows: Iterable[dict],
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Upsert income statement documents; returns number processed."""
    coll = mongo_client[mongo_db_name][cols.INCOME_STATEMENTS]
    ops: list[UpdateOne] = []
    count = 0

    for row in rows:
        doc = build_income_statement_doc(row)
        count += 1
        if dry_run:
            if verbose:
                click.secho(
                    f"[dry-run] Would upsert income_statement _id={doc['_id']} "
                    f"date={doc.get('date')} branch={doc.get('branch', {}).get('code')}",
                    fg="yellow",
                )
            continue
        ops.append(
            UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        )

    if not dry_run and ops:
        coll.bulk_write(ops, ordered=False)
        if verbose:
            click.secho(
                f"[income_statements] Upserted {len(ops)} document(s) into "
                f"{cols.qualified(mongo_db_name, cols.INCOME_STATEMENTS)}",
                fg="green",
            )

    return count


def sync_income_statements_in_window(
    pg_conn,
    mongo_client,
    mongo_db_name: str,
    start_iso: str,
    end_iso: str,
    *,
    dry_run: bool = False,
    verbose: bool = False,
    limit: int = 0,
) -> int:
    rows = _fetch_rows(
        pg_conn, INCOME_STATEMENT_BY_WINDOW_SQL, (start_iso, end_iso)
    )
    if limit and len(rows) > limit:
        rows = rows[:limit]
    if verbose:
        click.secho(
            f"[income_statements] Syncing {len(rows):,} record(s) "
            f"for window {start_iso} → {end_iso}",
            fg="cyan",
        )
    return upsert_income_statements(
        pg_conn,
        mongo_client,
        mongo_db_name,
        rows,
        dry_run=dry_run,
        verbose=verbose,
    )


def sync_income_statements_by_ids(
    pg_conn,
    mongo_client,
    mongo_db_name: str,
    income_statement_ids: Sequence[int],
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Upsert specific income statements (e.g. referenced by journal rows)."""
    ids = sorted({int(i) for i in income_statement_ids if int(i) > 0})
    if not ids:
        return 0

    rows = _fetch_rows(pg_conn, INCOME_STATEMENT_BY_IDS_SQL, (ids,))
    if verbose and rows:
        click.secho(
            f"[income_statements] Syncing {len(rows):,} record(s) by id "
            f"(from journal references)",
            fg="cyan",
        )
    return upsert_income_statements(
        pg_conn,
        mongo_client,
        mongo_db_name,
        rows,
        dry_run=dry_run,
        verbose=verbose,
    )


def collect_income_statement_ids_from_journals(
    journals_by_invoice: dict[int, list[dict]],
) -> list[int]:
    ids: set[int] = set()
    for journal_docs in journals_by_invoice.values():
        for doc in journal_docs:
            stmt = doc.get("incomeStatement") or {}
            stmt_id = int(stmt.get("_id") or 0)
            if stmt_id > 0:
                ids.add(stmt_id)
    return sorted(ids)
