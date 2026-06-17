from __future__ import annotations

from typing import Any, Dict, List

import click
from bson import ObjectId

from pg2mongo import collections as cols
from pg2mongo.builders.journal_build import build_journal_doc
from pg2mongo.utils import pg_row_to_dict


JOURNALS_BY_INVOICE_SQL = """
SELECT gj.id,
       gj.time_created,
       gj.time_modified,
       gj.trans_date,
       gj.trans_description,
       gj.debit,
       gj.credit,
       gj.ref_number,
       gj.account_chart_id,
       gj.transaction_type_id,
       gj.invoice_id,
       gj.payment_method_id,
       gj.branch_id,
       gj.customer_id,
       gj.created_by_id,
       gj.income_statement_id,
       gj.rate,
       gj.open_balance_temp,
       gj.transaction_id,
       gj.account_chart_description,
       gj.account_chart_display_name,
       gj.transaction_type_description,
       gj.account_chart_name,
       gj.account_type,
       COALESCE(gj.payment_method_payment_type, 'CASH'::character varying)
           AS payment_method_payment_type
FROM vwgeneral_journal gj
LEFT JOIN invoice inv ON inv.id = gj.invoice_id
WHERE gj.transaction_type_id IN (2, 3, 4, 8)
  AND inv.is_void = FALSE
  AND inv.registration = 'completed'
  AND gj.account_chart_id != 19
  AND inv.time_modified BETWEEN SYMMETRIC %s AND %s
ORDER BY gj.invoice_id, gj.transaction_id
"""


def load_journals_by_invoice(
    pg_conn,
    start_iso: str,
    end_iso: str,
    *,
    verbose: bool = False,
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Load journal rows for the invoice date window, grouped by Postgres ``invoice_id``.
    """
    journals: Dict[int, List[Dict[str, Any]]] = {}

    with pg_conn.cursor() as cur:
        cur.execute(JOURNALS_BY_INVOICE_SQL, (start_iso, end_iso))
        for row in cur:
            rec = pg_row_to_dict(row)
            invoice_id = int(rec.get("invoice_id") or 0)
            if invoice_id <= 0:
                continue
            journals.setdefault(invoice_id, []).append(build_journal_doc(rec))

    if verbose:
        entry_count = sum(len(v) for v in journals.values())
        click.secho(
            f"[journals] Loaded {entry_count:,} entr{'y' if entry_count == 1 else 'ies'} "
            f"for {len(journals):,} invoice(s)",
            fg="cyan",
        )

    return journals


def upsert_invoice_journals(
    mongo_client,
    mongo_db_name: str,
    invoice_id: ObjectId,
    journal_docs: List[Dict[str, Any]],
    session=None,
    *,
    verbose: bool = False,
) -> int:
    """Upsert journal documents for one invoice (same Mongo transaction as the invoice)."""
    if not journal_docs:
        return 0

    coll = mongo_client[mongo_db_name][cols.JOURNALS]
    written = 0

    for template in journal_docs:
        doc = dict(template)
        doc["invoice"] = {"id": invoice_id}
        old_id = doc["oldID"]

        coll.update_one(
            {"oldID": old_id},
            {"$set": doc},
            upsert=True,
            session=session,
        )
        written += 1

        if verbose:
            account = (doc.get("accounts") or [{}])[0]
            click.secho(
                f"[journal] upserted oldID={old_id} "
                f"account={account.get('name', '')}",
                fg="blue",
            )

    return written
