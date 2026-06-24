from __future__ import annotations

from typing import Optional

import click
from pymongo import UpdateOne

from pg2mongo.builders.employee_build import build_employee_doc
from pg2mongo import collections as cols
from pg2mongo.clients import connect_postgres, connect_mongo
from pg2mongo.cli.context import resolve_verbose, verbose_option
from pg2mongo.transfer.common import resolve_settings_from_ctx, close_connections_safe
from pg2mongo.transfer.progress import TransferProgress


EMPLOYEE_SQL = """
SELECT
    e.id,
    e.name,
    e.title,
    e.department,
    e.address       AS "address.address1",
    e.city          AS "address.city",
    e.zipcode       AS "address.zipcode",
    e.phone         AS phone1,
    e.email,
    e.country       AS "address.country",
    e.branch_id,
    b.code AS branch_code
FROM employee e
LEFT JOIN branch b ON b.id = e.branch_id
ORDER BY e.id
"""


@click.command("employee")
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of records processed (for testing).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview actions without writing to Mongo.",
)
@verbose_option
@click.pass_context
def employee_cmd(
    ctx: click.Context,
    limit: Optional[int],
    dry_run: bool,
    verbose: int,
):
    """
    Transfer employee records from Postgres → MongoDB (employees collection).
    """
    verbose = resolve_verbose(ctx, verbose)
    settings = resolve_settings_from_ctx(ctx, verbose=verbose)

    pg_conn = None
    mongo_client = None

    try:
        # 1) Connect to DBs
        pg_conn = connect_postgres(settings, verbose=verbose)
        mongo_client = connect_mongo(settings, verbose=verbose)

        db = mongo_client[settings.mongo.db]
        coll = db[cols.EMPLOYEES]

        # 2) Run query against Postgres
        if verbose:
            click.secho("[employees] Executing Postgres query…", fg="cyan")

        with pg_conn.cursor() as cur:
            cur.execute(EMPLOYEE_SQL)
            rows = cur.fetchall()

        total_rows = len(rows)
        if total_rows == 0:
            click.secho("[employees] No records found in employee table.", fg="yellow")
            return

        if limit is not None:
            rows = rows[:limit]

        if verbose:
            msg = f"[employees] Retrieved {len(rows)} rows from Postgres"
            if limit is not None:
                msg += f" (limit={limit})"
            click.secho(msg, fg="cyan")

        progress = TransferProgress(
            label="Employees",
            total=total_rows,
            limit=limit or 0,
            verbose=verbose,
        )
        progress.announce()

        # 3) Build bulk upsert operations
        ops: list[UpdateOne] = []
        with progress:
            for row in rows:
                doc = build_employee_doc(row)
                branch = doc.get("branch") or {}
                hint = f"id={doc.get('_id')} name={doc.get('name')}"
                if progress.enabled(2):
                    hint += f" branch={branch.get('code', '')} phone1={doc.get('phone1', '')}"
                progress.step(hint, emit=verbose)

                if progress.enabled(4):
                    progress.secho(f"[employee] doc={doc!r}", fg="white")

                ops.append(
                    UpdateOne(
                        {"_id": doc["_id"]},
                        {
                            "$set": doc,
                            "$unset": {
                                "phone1": "",
                                "phone2": "",
                            },
                        },
                        upsert=True,
                    )
                )

        if dry_run:
            click.secho(
                f"[DRY-RUN] would upsert {len(ops)} documents into "
                f"{cols.qualified(settings.mongo.db, cols.EMPLOYEES)}",
                fg="yellow",
            )
            return

        # 4) Execute bulk_write
        result = coll.bulk_write(ops, ordered=False)

        click.secho(
            (
                f"[employees] Upsert complete → "
                f"matched={result.matched_count}, "
                f"modified={result.modified_count}, "
                f"upserted={len(result.upserted_ids)}"
            ),
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)
