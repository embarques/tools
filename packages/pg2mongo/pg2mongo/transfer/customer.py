from __future__ import annotations

from typing import Optional

import click
from pymongo.errors import PyMongoError

from pg2mongo import collections as cols
from pg2mongo.cli.context import resolve_verbose, verbose_option
from pg2mongo.transfer.common import (
    resolve_settings_from_ctx,
    connect_postgres_and_mongo,
    get_date_window,
    close_connections_safe,
)
from pg2mongo.transfer.progress import TransferProgress, count_sql_rows
from pg2mongo.builders.customer_build import build_customer_doc


_BATCH_SIZE = 500

CUSTOMER_COUNT_SQL = """
SELECT COUNT(*)::bigint AS cnt
FROM vwcustomer_api c
WHERE c.time_modified BETWEEN SYMMETRIC %s AND %s
"""

CUSTOMER_SELECT_SQL = """
SELECT c.id,
       c.c_type AS "cus_type",
       c.branch_id,
       c.name,
       c.phone1,
       c.phone2,
       c.id_number,
       c.active,
       c."address.address1",
       c."address.apt",
       c."time_created",
       c."created_by_id",
       c."address.address2",
       c."address.city",
       c."address.state",
       c."address.zipcode",
       c."address.country",
       b.code AS branch_code,
       b.name AS branch_name
FROM vwcustomer_api c
LEFT JOIN branch b ON b.id = c.branch_id
WHERE c.time_modified BETWEEN SYMMETRIC %s AND %s
ORDER BY c.time_modified ASC
"""


@click.command("customer")
@click.option(
    "--start-date",
    help="Start date (YYYY-MM-DD or MM-DD-YYYY). If omitted, auto from Mongo updatedAt.",
)
@click.option(
    "--end-date",
    help="End date (YYYY-MM-DD or MM-DD-YYYY). Defaults to today 23:59:59 UTC.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Do not write to Mongo, only simulate and report.",
)
@click.option(
    "--limit",
    type=int,
    default=0,
    help="Limit number of records processed (0 = no limit).",
)
@verbose_option
@click.pass_context
def customer_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
    verbose: int,
):
    """
    Transfer customers from Postgres vwcustomer_api to Mongo customers collection.
    """
    verbose = resolve_verbose(ctx, verbose)
    verbosity = verbose
    settings = resolve_settings_from_ctx(ctx, verbose=verbose)
    pg_conn = None
    mongo_client = None

    try:
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)
        coll = mongo_client[settings.mongo.db][cols.CUSTOMERS]

        start_iso, end_iso = get_date_window(
            coll,
            start_date,
            end_date,
            verbose,
        )

        if verbose:
            click.secho(
                f"Running customer query between {start_iso} and {end_iso}",
                fg="cyan",
            )

        total = count_sql_rows(pg_conn, CUSTOMER_COUNT_SQL, (start_iso, end_iso))
        progress = TransferProgress(
            label="Customers",
            total=total,
            limit=limit,
            verbose=verbose,
        )
        progress.announce()

        with pg_conn.cursor() as cur:
            cur.execute(CUSTOMER_SELECT_SQL, (start_iso, end_iso))

            batch = []

            with progress:
                for row in cur:
                    if limit and progress.current >= limit:
                        break

                    doc = build_customer_doc(row)
                    hint = f"oldID={doc.get('oldID')} name={doc.get('name')}"
                    if verbosity >= 2:
                        branch = doc.get("branch") or {}
                        primary_phone = doc.get("phone1") or ""
                        hint += (
                            f" type={doc.get('customerType')} "
                            f"phone={primary_phone} branch={branch.get('code', '')}"
                        )
                    progress.step(hint, emit=verbose)

                    if verbosity >= 4:
                        progress.secho(f"[customer] doc={doc!r}", fg="white")

                    batch.append(doc)

                    if len(batch) >= _BATCH_SIZE:
                        _flush_customer_batch(
                            coll,
                            batch,
                            dry_run,
                            progress.current,
                            verbose=verbose,
                            progress=progress,
                        )
                        batch.clear()

                if batch:
                    _flush_customer_batch(
                        coll,
                        batch,
                        dry_run,
                        progress.current,
                        verbose=verbose,
                        progress=progress,
                    )
                    batch.clear()

            click.secho(
                f"✅ Customer transfer complete. {progress.summary(dry_run=dry_run)}, dry_run={dry_run}",
                fg="green",
            )

    finally:
        close_connections_safe(pg_conn, mongo_client)


def _flush_customer_batch(
    coll,
    batch,
    dry_run: bool,
    processed: int,
    *,
    verbose: bool = False,
    progress: TransferProgress | None = None,
):
    """
    Upsert customers by oldID.
    """
    if dry_run:
        if verbose:
            for doc in batch:
                msg = f"[dry-run] Would upsert customer oldID={doc.get('oldID')} name={doc.get('name')}"
                if progress:
                    progress.secho(msg, fg="yellow")
                else:
                    click.secho(msg, fg="yellow")
        else:
            click.secho(
                f"[dry-run] Would upsert {len(batch)} customers (processed so far: {processed})",
                fg="yellow",
            )
        return

    requests = []
    from pymongo import UpdateOne

    for doc in batch:
        old_id = doc.get("oldID")
        if old_id is None:
            click.secho(
                "[warn] customer missing oldID; skipping", fg="yellow"
            )
            continue

        # Always update updatedAt on write
        from datetime import datetime, timezone

        doc["updatedAt"] = datetime.now(timezone.utc)

        requests.append(
            UpdateOne(
                {"oldID": old_id},
                {
                    "$set": doc,
                    "$unset": {
                        "phones": "",
                    },
                },
                upsert=True,
            )
        )

    if not requests:
        return

    try:
        result = coll.bulk_write(requests, ordered=False)
        if verbose:
            message = (
                f"[batch] customers upserted={result.upserted_count} "
                f"matched={result.matched_count} modified={result.modified_count}"
            )
            if progress:
                progress.secho(message, fg="cyan")
            else:
                click.secho(message, fg="cyan")
    except PyMongoError as exc:
        click.secho("❌ Error during customer bulk_write:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
