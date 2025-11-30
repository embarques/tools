from __future__ import annotations

from typing import Optional

import click
from pymongo import UpdateOne
from pymongo.errors import PyMongoError

from pg2mongo.transfer.common import (
    resolve_settings,
    connect_postgres_and_mongo,
    get_date_window,
    close_connections_safe,
)
from pg2mongo.builders.invoice_build import build_invoice_doc


_BATCH_SIZE = 200


@click.command("invoice")
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
def invoice_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
):
    """
    Transfer invoices from Postgres vwinvoice_api to Mongo invoices collection.
    (Header-focused; detail/journal logic can be extended as needed.)
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
            collection="invoices",
        )

        sql = """
        SELECT id,
               number,
               time_created,
               time_modified,
               is_void,
               invoice_date,
               branch_id,
               container_id,
               container_designation,
               "driver_id",
               "user_id",
               "user.name",
               "driver.name",
               cost,
               paid_status,
               paid_region,
               balance,
               payment,
               discount,
               recharge,

               "sender.id",
               "sender.cus_type",
               "sender.branch_id",
               "sender.name",
               "sender.phone1",
               "sender.phone2",
               "sender.address.address1",
               "sender.address.apt",
               "sender.time_created",
               "sender.created_by_id",
               "sender.address.address2",
               "sender.address.city",
               "sender.address.state",
               "sender.address.zipcode",
               "sender.address.country",

               "receiver.id",
               "receiver.cus_type",
               "receiver.branch_id",
               "receiver.name",
               "receiver.phone1",
               "receiver.phone2",
               "receiver.address.address1",
               "receiver.address.apt",
               "receiver.time_created",
               "receiver.created_by_id",
               "receiver.address.address2",
               "receiver.address.city",
               "receiver.address.state",
               "receiver.address.zipcode",
               "receiver.address.country"
        FROM vwinvoice_api
        WHERE is_void = FALSE
          AND registration = 'completed'
          AND time_modified BETWEEN SYMMETRIC %s AND %s
        ORDER BY invoice_date ASC
        """

        if verbose:
            click.secho(
                f"Running invoice query between {start_iso} and {end_iso}",
                fg="cyan",
            )

        coll = mongo_client[settings.mongo.db]["invoices"]

        processed = 0
        batch = []

        with pg_conn.cursor() as cur:
            cur.execute(sql, (start_iso, end_iso))

            for row in cur:
                processed += 1
                if limit and processed > limit:
                    break

                doc = build_invoice_doc(row)
                batch.append(doc)

                if len(batch) >= _BATCH_SIZE:
                    _flush_invoice_batch(coll, batch, dry_run, processed)
                    batch.clear()

        if batch:
            _flush_invoice_batch(coll, batch, dry_run, processed)
            batch.clear()

        click.secho(
            f"✅ Invoice transfer complete. Processed={processed}, dry_run={dry_run}",
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)


def _flush_invoice_batch(coll, batch, dry_run: bool, processed: int):
    if dry_run:
        click.secho(
            f"[dry-run] Would upsert {len(batch)} invoices (processed so far: {processed})",
            fg="yellow",
        )
        return

    requests = []

    from datetime import datetime, timezone

    for doc in batch:
        old_id = doc.get("oldID")
        if old_id is None:
            click.secho(
                "[warn] invoice missing oldID; skipping",
                fg="yellow",
            )
            continue

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
            f"[batch] invoices upserted={result.upserted_count} matched={result.matched_count} modified={result.modified_count}",
            fg="blue",
        )
    except PyMongoError as exc:
        click.secho("❌ Error during invoice bulk_write:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
