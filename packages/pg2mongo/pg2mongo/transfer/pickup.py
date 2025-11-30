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
from pg2mongo.builders.pickup_build import build_pickup_doc
from pg2mongo.utils import get_next_sequence  # ← moved here


_BATCH_SIZE = 200


@click.command("pickup")
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
def pickup_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
):
    """
    Transfer pickups from Postgres vwpickup_api to Mongo pickups collection.
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
            collection="pickups",
        )

        sql = """
        SELECT id,
               pickup_date,
               pickup_created,
               pickup_modified,
               completed,
               "user.id",
               "user.name",
               "employee.id",
               "employee.name",
               "branch.id",
               "branch.code",
               sector_id,
               sector_name,
               purpose,
               comment,
               "sender.id",
               "sender.name",
               "sender.phone1",
               "sender.phone2",
               "sender.address.address1",
               "sender.address.apt",
               "sender.address.address2",
               "sender.address.city",
               "sender.address.state",
               "sender.address.zipcode",
               "sender.address.country",
               "receiver.id",
               "receiver.name",
               "receiver.phone1",
               "receiver.phone2",
               "receiver.address.address1",
               "receiver.address.apt",
               "receiver.address.address2",
               "receiver.address.city",
               "receiver.address.state",
               "receiver.address.country"
        FROM vwpickup_api
        WHERE pickup_modified BETWEEN SYMMETRIC %s AND %s
        ORDER BY pickup_date ASC
        """

        if verbose:
            click.secho(
                f"Running pickup query between {start_iso} and {end_iso}",
                fg="cyan",
            )

        db = mongo_client[settings.mongo.db]
        coll = db["pickups"]

        processed = 0
        batch_docs = []

        with pg_conn.cursor() as cur:
            cur.execute(sql, (start_iso, end_iso))

            for row in cur:
                processed += 1
                if limit and processed > limit:
                    break

                doc = build_pickup_doc(row)
                batch_docs.append(doc)

                if len(batch_docs) >= _BATCH_SIZE:
                    _flush_pickup_batch(db, coll, batch_docs, dry_run, processed)
                    batch_docs.clear()

        if batch_docs:
            _flush_pickup_batch(db, coll, batch_docs, dry_run, processed)
            batch_docs.clear()

        click.secho(
            f"✅ Pickup transfer complete. Processed={processed}, dry_run={dry_run}",
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)


def _flush_pickup_batch(db, coll, docs, dry_run: bool, processed: int):
    if dry_run:
        click.secho(
            f"[dry-run] Would upsert {len(docs)} pickups (processed so far: {processed})",
            fg="yellow",
        )
        return

    requests = []
    from datetime import datetime, timezone

    for doc in docs:
        old_id = doc.get("oldID")
        if old_id is None:
            click.secho("[warn] pickup missing oldID; skipping", fg="yellow")
            continue

        # Assign numeric _id via counters
        try:
            doc["_id"] = get_next_sequence(db, "pickup_id")
        except Exception as exc:
            click.secho(
                f"❌ Failed to get next pickup_id for oldID={old_id}: {exc}",
                fg="red",
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
            f"[batch] pickups upserted={result.upserted_count} "
            f"matched={result.matched_count} modified={result.modified_count}",
            fg="blue",
        )
    except PyMongoError as exc:
        click.secho("❌ Error during pickup bulk_write:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
