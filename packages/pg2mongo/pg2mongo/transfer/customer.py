from __future__ import annotations

from typing import Optional

import click
from pymongo.errors import PyMongoError

from pg2mongo.transfer.common import (
    resolve_settings,
    connect_postgres_and_mongo,
    get_date_window,
    close_connections_safe,
)
from pg2mongo.builders.customer_build import build_customer_doc


_BATCH_SIZE = 500


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
@click.pass_context
def customer_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
):
    """
    Transfer customers from Postgres vwcustomer_api to Mongo customers collection.
    """
    config_path = ctx.obj.get("config_path")
    verbose = ctx.obj.get("verbose", False)

    settings = resolve_settings(config_path, verbose)
    pg_conn = None
    mongo_client = None

    try:
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)

        start_iso, end_iso = get_date_window(
            mongo_client,
            settings,
            start_date,
            end_date,
            verbose,
            collection="customers",
        )

        sql = """
        SELECT id,
               c_type AS "cus_type",
               branch_id,
               name,
               phone1,
               phone2,
               id_number,
               active,
               "address.address1",
               "address.apt",
               "time_created",
               "created_by_id",
               "address.address2",
               "address.city",
               "address.state",
               "address.zipcode",
               "address.country"
        FROM vwcustomer_api
        WHERE time_modified BETWEEN SYMMETRIC %s AND %s
        ORDER BY time_modified ASC
        """

        if verbose:
            click.secho(
                f"Running customer query between {start_iso} and {end_iso}",
                fg="cyan",
            )

        with pg_conn.cursor() as cur:
            cur.execute(sql, (start_iso, end_iso))

            coll = mongo_client[settings.mongo.db]["customers"]

            processed = 0
            batch = []

            for row in cur:
                processed += 1
                if limit and processed > limit:
                    break

                doc = build_customer_doc(row)
                batch.append(doc)

                if len(batch) >= _BATCH_SIZE:
                    _flush_customer_batch(coll, batch, dry_run, processed)
                    batch.clear()

            if batch:
                _flush_customer_batch(coll, batch, dry_run, processed)
                batch.clear()

            click.secho(
                f"✅ Customer transfer complete. Processed={processed}, dry_run={dry_run}",
                fg="green",
            )

    finally:
        close_connections_safe(pg_conn, mongo_client)


def _flush_customer_batch(coll, batch, dry_run: bool, processed: int):
    """
    Upsert customers by oldID.
    """
    if dry_run:
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
                {"$set": doc},
                upsert=True,
            )
        )

    if not requests:
        return

    try:
        result = coll.bulk_write(requests, ordered=False)
        click.secho(
            f"[batch] upserted={result.upserted_count} matched={result.matched_count} modified={result.modified_count}",
            fg="blue",
        )
    except PyMongoError as exc:
        click.secho("❌ Error during customer bulk_write:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
