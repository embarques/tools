from __future__ import annotations

from typing import Optional

import click
from pymongo import UpdateOne

from pg2mongo.builders.employee_build import build_employee_doc
from pg2mongo.clients import connect_postgres, connect_mongo
from pg2mongo.transfer.common import resolve_settings, close_connections_safe


EMPLOYEE_SQL = """
SELECT
    id,
    name,
    title,
    department,
    address       AS "address.address1",
    city          AS "address.city",
    zipcode       AS "address.zipcode",
    phone         AS phone1,
    email,
    country       AS "address.country",
    branch_id
FROM employee
ORDER BY id
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
@click.pass_context
def employee_cmd(
    ctx: click.Context,
    limit: Optional[int],
    dry_run: bool,
):
    """
    Transfer employee records from Postgres → MongoDB (employees collection).
    """
    config_path = ctx.obj.get("config_path")
    verbose = bool(ctx.obj.get("verbose"))

    settings = resolve_settings(config_path, verbose)

    pg_conn = None
    mongo_client = None

    try:
        # 1) Connect to DBs
        pg_conn = connect_postgres(settings, verbose=verbose)
        mongo_client = connect_mongo(settings, verbose=verbose)

        db = mongo_client[settings.mongo.db]
        coll = db["employees"]

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

        # 3) Build bulk upsert operations
        ops: list[UpdateOne] = []
        for idx, row in enumerate(rows, start=1):
            doc = build_employee_doc(row)

            if dry_run and verbose:
                click.secho(
                    f"[employees] DRY-RUN {idx}/{len(rows)} _id={doc['_id']} name={doc['name']}",
                    fg="white",
                )

            ops.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {"$set": doc},
                    upsert=True,
                )
            )

        if dry_run:
            click.secho(
                f"[DRY-RUN] employees: would upsert {len(ops)} documents into {settings.mongo.db}.employees",
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
