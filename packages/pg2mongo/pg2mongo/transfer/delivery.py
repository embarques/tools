from __future__ import annotations

from datetime import datetime
from typing import Optional

import click
from pymongo import UpdateOne

from pg2mongo.builders.delivery_build import build_delivery_doc
from pg2mongo import collections as cols
from pg2mongo.clients import connect_postgres, connect_mongo
from pg2mongo.cli.context import get_verbose
from pg2mongo.transfer.common import resolve_settings_from_ctx, close_connections_safe


DELIVERY_SQL = """
SELECT
    id,
    gen_num,
    delivery_date,
    delivery_number,
    container_id,
    container_designation,
    employee_id,
    employee_name,
    helper1_id,
    helper1_name,
    helper2_id,
    helper2_name
FROM vwdelivery_api
WHERE date_part('year', delivery_date) BETWEEN %s AND %s
ORDER BY id
"""


@click.command("delivery")
@click.option(
    "--start-year",
    type=int,
    default=2022,
    help="Start year for deliveries (delivery_date year). Defaults to 2022.",
)
@click.option(
    "--end-year",
    type=int,
    default=None,
    help="End year for deliveries (delivery_date year). Defaults to current year.",
)
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
def delivery_cmd(
    ctx: click.Context,
    start_year: int,
    end_year: Optional[int],
    limit: Optional[int],
    dry_run: bool,
):
    """
    Transfer delivery records from Postgres → MongoDB (deliveries collection).
    """
    verbose = get_verbose(ctx)

    if end_year is None:
        end_year = datetime.utcnow().year

    settings = resolve_settings_from_ctx(ctx)

    pg_conn = None
    mongo_client = None

    try:
        # 1) Connect DBs
        pg_conn = connect_postgres(settings, verbose=verbose)
        mongo_client = connect_mongo(settings, verbose=verbose)

        db = mongo_client[settings.mongo.db]
        coll = db[cols.DELIVERIES]

        if verbose:
            click.secho(
                f"[deliveries] Year range: {start_year} → {end_year}",
                fg="cyan",
            )
            click.secho(
                f"[deliveries] Querying Postgres vwdelivery_api…",
                fg="cyan",
            )

        # 2) Run query
        with pg_conn.cursor() as cur:
            cur.execute(DELIVERY_SQL, (start_year, end_year))
            rows = cur.fetchall()

        total_rows = len(rows)
        if total_rows == 0:
            click.secho(
                "[deliveries] No delivery records found for given year range.",
                fg="yellow",
            )
            return

        if limit is not None:
            rows = rows[:limit]

        if verbose:
            msg = f"[deliveries] Retrieved {len(rows)} rows from Postgres"
            if limit is not None:
                msg += f" (limit={limit})"
            click.secho(msg, fg="cyan")

        # 3) Build bulk upsert operations
        ops: list[UpdateOne] = []
        for idx, row in enumerate(rows, start=1):
            doc = build_delivery_doc(row)

            if dry_run and verbose:
                click.secho(
                    f"[deliveries] DRY-RUN {idx}/{len(rows)} "
                    f"_id={doc['_id']} name={doc['name']}",
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
                f"[DRY-RUN] would upsert {len(ops)} documents into "
                f"{cols.qualified(settings.mongo.db, cols.DELIVERIES)}",
                fg="yellow",
            )
            return

        # 4) Execute bulk_write
        result = coll.bulk_write(ops, ordered=False)

        click.secho(
            (
                f"[deliveries] Upsert complete → "
                f"matched={result.matched_count}, "
                f"modified={result.modified_count}, "
                f"upserted={len(result.upserted_ids)}"
            ),
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)
