from __future__ import annotations

from typing import Optional

import click
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

from pg2mongo import collections as cols
from pg2mongo.mongo import get_collection
from pg2mongo.builders.invoice_build import build_invoice_doc
from pg2mongo.builders.invoice_detail_build import (
    add_invoice_details,
    load_invoice_details,
)
from pg2mongo.transfer.common import (
    resolve_settings,
    connect_postgres_and_mongo,
    get_date_window,
    close_connections_safe,
)


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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output.",
)
@click.pass_context
def invoice_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
    verbose: bool,
):
    """
    Main CLI command to transfer invoices from Postgres -> MongoDB.

    For each invoice:
      1. Build invoice header object from Postgres row.
      2. Within a MongoDB transaction:
         - Upsert the invoice header.
         - Load invoiceDetail + barcode rows from Postgres.
         - Insert invoice details into their collection.
         - Update invoice.invoiceDetails with inserted IDs.
      3. If any step fails, the transaction rolls back and the invoice is NOT created.

    This guarantees a COMPLETE invoice (header + details + barcodes)
    is always recorded in MongoDB, never a partial document.
    """

    config_path = ctx.obj.get("config_path")
    verbose = verbose or bool(ctx.obj.get("verbose", False))
    settings = resolve_settings(config_path, verbose)

    pg_conn = None
    mongo_client = None

    try:
        # Establish connections to Postgres and MongoDB
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)

        mongo_db_name = settings.mongo.db

        # MongoDB invoices collection
        coll = get_collection(mongo_client, mongo_db_name, cols.INVOICES)

        # Calculate time window to fetch invoices from Postgres
        start_iso, end_iso = get_date_window(
            coll=coll,
            start_date=start_date,
            end_date=end_date,
            verbose=verbose,
        )

        # Query to pull invoice header information from Postgres
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
                f"[query] Running invoice query between {start_iso} and {end_iso}",
                fg="cyan",
            )

        processed = 0

        # Execute invoice query
        with pg_conn.cursor() as cur:
            cur.execute(sql, (start_iso, end_iso))

            # Process invoice rows one at a time
            for row in cur:
                processed += 1
                if limit and processed > limit:
                    break

                # Process this invoice: upsert header + insert details
                _process_single_invoice(
                    pg_conn=pg_conn,
                    mongo_client=mongo_client,
                    mongo_db_name=mongo_db_name,
                    coll=coll,
                    row=row,
                    dry_run=dry_run,
                    verbose=verbose,
                )

        click.secho(
            f"✅ Invoice transfer complete. Processed={processed}, dry_run={dry_run}",
            fg="green",
        )

    finally:
        # Always close DB connections
        close_connections_safe(pg_conn, mongo_client)


def _process_single_invoice(
    pg_conn,
    mongo_client,
    mongo_db_name: str,
    coll,
    row,
    dry_run: bool,
    verbose: bool,
):
    """
    Handles the full ingestion of a single invoice:
       - Build invoice header
       - Start MongoDB transaction
       - Upsert invoice header
       - Load invoice details + barcodes (from Postgres)
       - Insert invoice details
       - Update invoice with reference IDs
       - Commit transaction

    If any step fails, MongoDB automatically rolls back the entire invoice.
    """

    # Convert SQL row → invoice MongoDB document
    doc = build_invoice_doc(row)
    old_id = doc.get("oldID")
    number = doc.get("number")

    if old_id is None:
        click.secho("[warn] invoice missing oldID; skipping", fg="yellow")
        return

    if verbose:
        click.secho(
            f"\n[invoice] Processing invoice oldID={old_id}, number={number}",
            fg="white",
        )

    # Timestamp refresh — ensures invoice gets updatedAt on every sync
    doc["updatedAt"] = datetime.now(timezone.utc)

    # ------------------------
    # DRY RUN MODE
    # ------------------------
    if dry_run:
        # Load associated details + barcodes just for reporting
        details = load_invoice_details(pg_conn, old_id)
        detail_count = len(details)
        barcode_count = sum(len(d.get("barcodes", [])) for d in details)

        click.secho(
            f"[dry-run] Would upsert invoice oldID={old_id}, number={number}",
            fg="yellow",
        )
        click.secho(
            f"[dry-run] Would insert invoiceDetails={detail_count}, "
            f"barcodes={barcode_count}",
            fg="yellow",
        )
        return

    # Real write mode below
    invoices_coll = coll

    # Use MongoDB session for per-invoice transaction
    with mongo_client.start_session() as session:

        def txn_ops(sess):
            # -----------------------------------------------------------
            # 1) UPSERT invoice header (using oldID as natural identifier)
            # -----------------------------------------------------------
            result = invoices_coll.update_one(
                {"oldID": old_id},
                {"$set": doc},
                upsert=True,
                session=sess,
            )

            # Retrieve invoice MongoDB _id
            if result.upserted_id is not None:
                invoice_id = result.upserted_id
                inserted = True
            else:
                existing = invoices_coll.find_one(
                    {"oldID": old_id},
                    {"_id": 1},
                    session=sess,
                )
                if not existing:
                    raise RuntimeError(
                        f"Invoice oldID={old_id} not found after upsert."
                    )
                invoice_id = existing["_id"]
                inserted = False

            if verbose:
                action = "inserted" if inserted else "updated"
                click.secho(
                    f"[invoice] Header {action}: _id={invoice_id}, oldID={old_id}",
                    fg="blue",
                )

            # -----------------------------------------------------------
            # 2) INSERT invoice details + barcodes
            #
            #    add_invoice_details:
            #      - Loads invoice details + barcodes from Postgres
            #      - Inserts them into invoiceDetails collection
            #      - Updates invoice.invoiceDetails with the new IDs
            # -----------------------------------------------------------
            add_invoice_details(
                pg_conn=pg_conn,
                mongo_client=mongo_client,
                mongo_db_name=mongo_db_name,
                invoice_old_id=old_id,
                invoice_id=invoice_id,
                session=sess,
                verbose=verbose,
            )

        # Execute transaction for this invoice
        try:
            session.with_transaction(txn_ops)
            if verbose:
                click.secho(
                    f"[ok] Invoice oldID={old_id} fully committed (header + details)",
                    fg="green",
                )
        except PyMongoError as exc:
            click.secho(
                f"❌ MongoDB error migrating invoice oldID={old_id}: {exc}",
                fg="red",
            )
        except Exception as exc:
            click.secho(
                f"❌ Unexpected error migrating invoice oldID={old_id}: {exc}",
                fg="red",
            )
