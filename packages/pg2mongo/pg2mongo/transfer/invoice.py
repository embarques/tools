from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import click
from pymongo.errors import PyMongoError

from pg2mongo import collections as cols
from pg2mongo.mongo import get_collection
from pg2mongo.builders.invoice_build import build_invoice_doc
from pg2mongo.builders.invoice_detail_build import (
    add_invoice_details,
    load_invoice_details,
)
from pg2mongo.builders.journal_sync import (
    load_journals_by_invoice,
    upsert_invoice_journals,
)
from pg2mongo.builders.income_statement_sync import (
    collect_income_statement_ids_from_journals,
    sync_income_statements_by_ids,
    sync_income_statements_in_window,
)
from pg2mongo.transfer.common import (
    resolve_settings_from_ctx,
    connect_postgres_and_mongo,
    get_date_window,
    close_connections_safe,
)
from pg2mongo.transfer.progress import TransferProgress, count_sql_rows
from pg2mongo.cli.context import resolve_verbose, verbose_option


INVOICE_COUNT_SQL = """
SELECT COUNT(*)::bigint AS cnt
FROM vwinvoice_api v
WHERE v.is_void = FALSE
  AND v.registration = 'completed'
  AND v.time_modified BETWEEN SYMMETRIC %s AND %s
"""

INVOICE_SELECT_SQL = """
SELECT v.id,
       v.number,
       v.time_created,
       v.time_modified,
       v.is_void,
       v.invoice_date,
       v.branch_id,
       COALESCE(b.code, ''::character varying) AS branch_code,
       v.container_id,
       v.container_designation,
       v.driver_id,
       v.user_id,
       COALESCE(u.username, ''::character varying) AS "user.name",
       COALESCE(driver.name, ''::character varying) AS "driver.name",
       v.cost,
       v.paid_status,
       v.paid_region,
       v.balance,
       v.payment,
       v.discount,
       v.recharge,

       v."sender.id",
       v."sender.cus_type",
       v."sender.branch_id",
       v."sender.name",
       v."sender.phone1",
       v."sender.phone2",
       v."sender.address.address1",
       v."sender.address.apt",
       v."sender.time_created",
       v."sender.created_by_id",
       v."sender.address.address2",
       v."sender.address.city",
       v."sender.address.state",
       v."sender.address.zipcode",
       v."sender.address.country",

       v."receiver.id",
       v."receiver.cus_type",
       v."receiver.branch_id",
       v."receiver.name",
       v."receiver.phone1",
       v."receiver.phone2",
       v."receiver.address.address1",
       v."receiver.address.apt",
       v."receiver.time_created",
       v."receiver.created_by_id",
       v."receiver.address.address2",
       v."receiver.address.city",
       v."receiver.address.state",
       v."receiver.address.zipcode",
       v."receiver.address.country"
FROM vwinvoice_api v
LEFT JOIN branch b ON b.id = v.branch_id
LEFT JOIN auth_user u ON u.id = v.user_id
LEFT JOIN employee driver ON driver.id = v.driver_id
WHERE v.is_void = FALSE
  AND v.registration = 'completed'
  AND v.time_modified BETWEEN SYMMETRIC %s AND %s
ORDER BY v.invoice_date ASC
"""


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
@verbose_option
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
         - Update invoice document with detail reference IDs.
         - Upsert journal entries into the journals collection.
      3. If any step fails, the transaction rolls back and the invoice is NOT created.

    This guarantees a COMPLETE invoice (header + details + barcodes)
    is always recorded in MongoDB, never a partial document.
    """

    verbose = resolve_verbose(ctx, verbose)
    settings = resolve_settings_from_ctx(ctx, verbose=verbose)

    pg_conn = None
    mongo_client = None

    try:
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)

        mongo_db_name = settings.mongo.db
        coll = get_collection(mongo_client, mongo_db_name, cols.INVOICES)

        start_iso, end_iso = get_date_window(
            coll=coll,
            start_date=start_date,
            end_date=end_date,
            verbose=verbose,
        )

        if verbose:
            click.secho(
                f"[query] Running invoice query between {start_iso} and {end_iso}",
                fg="cyan",
            )

        total = count_sql_rows(pg_conn, INVOICE_COUNT_SQL, (start_iso, end_iso))
        progress = TransferProgress(
            label="Invoices",
            total=total,
            limit=limit,
            verbose=verbose,
        )
        progress.announce()

        journals_by_invoice = load_journals_by_invoice(
            pg_conn, start_iso, end_iso, verbose=verbose
        )

        if not dry_run:
            sync_income_statements_in_window(
                pg_conn,
                mongo_client,
                mongo_db_name,
                start_iso,
                end_iso,
                verbose=verbose,
            )
            journal_stmt_ids = collect_income_statement_ids_from_journals(
                journals_by_invoice
            )
            sync_income_statements_by_ids(
                pg_conn,
                mongo_client,
                mongo_db_name,
                journal_stmt_ids,
                verbose=verbose,
            )
        elif verbose:
            journal_stmt_ids = collect_income_statement_ids_from_journals(
                journals_by_invoice
            )
            click.secho(
                f"[dry-run] Would sync income_statements in date window and "
                f"{len(journal_stmt_ids)} referenced by journals",
                fg="yellow",
            )

        with progress:
            with pg_conn.cursor() as cur:
                cur.execute(INVOICE_SELECT_SQL, (start_iso, end_iso))

                for row in cur:
                    if limit and progress.current >= limit:
                        break

                    doc = build_invoice_doc(row)
                    hint = f"oldID={doc.get('oldID')} number={doc.get('number')}"
                    progress.step(hint, emit=verbose)

                    _process_single_invoice(
                        pg_conn=pg_conn,
                        mongo_client=mongo_client,
                        mongo_db_name=mongo_db_name,
                        coll=coll,
                        row=row,
                        dry_run=dry_run,
                        verbose=verbose,
                        progress=progress,
                        journals_by_invoice=journals_by_invoice,
                    )

        click.secho(
            f"✅ Invoice transfer complete. {progress.summary(dry_run=dry_run)}, "
            f"dry_run={dry_run}",
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)


def _process_single_invoice(
    pg_conn,
    mongo_client,
    mongo_db_name: str,
    coll,
    row,
    dry_run: bool,
    verbose: bool,
    progress: TransferProgress,
    journals_by_invoice: dict[int, list],
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

    doc = build_invoice_doc(row)
    old_id = doc.get("oldID")
    number = doc.get("number")

    if old_id is None:
        progress.secho("invoice missing oldID; skipping", fg="yellow")
        return

    journal_docs = journals_by_invoice.get(int(old_id), [])

    doc["updatedAt"] = datetime.now(timezone.utc)

    if dry_run:
        details = load_invoice_details(pg_conn, old_id, verbose=verbose)
        detail_count = len(details)
        barcode_count = sum(len(d.get("barcodes", [])) for d in details)

        if verbose:
            progress.secho(
                f"[dry-run] Would upsert invoice oldID={old_id}, number={number}",
                fg="yellow",
            )
            progress.secho(
                f"[dry-run] Would insert {detail_count} doc(s) into "
                f"{cols.INVOICE_DETAILS}, barcodes={barcode_count}",
                fg="yellow",
            )
            progress.secho(
                f"[dry-run] Would upsert {len(journal_docs)} journal(s) into "
                f"{cols.JOURNALS}",
                fg="yellow",
            )
        return

    invoices_coll = coll

    with mongo_client.start_session() as session:

        def txn_ops(sess):
            result = invoices_coll.update_one(
                {"oldID": old_id},
                {
                    "$set": doc,
                    "$unset": {
                        "user": "",
                        "driver": "",
                        "invoice_details": "",
                    },
                },
                upsert=True,
                session=sess,
            )

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
                progress.secho(
                    f"[invoice] Header {action}: _id={invoice_id}, oldID={old_id}",
                    fg="blue",
                )

            add_invoice_details(
                pg_conn=pg_conn,
                mongo_client=mongo_client,
                mongo_db_name=mongo_db_name,
                invoice_old_id=old_id,
                invoice_id=invoice_id,
                session=sess,
                verbose=verbose,
            )

            upsert_invoice_journals(
                mongo_client,
                mongo_db_name,
                invoice_id,
                journal_docs,
                session=sess,
                verbose=verbose,
            )

        try:
            session.with_transaction(txn_ops)
            if verbose:
                progress.secho(
                    f"[ok] Invoice oldID={old_id} fully committed "
                    f"(header + details + {len(journal_docs)} journal(s))",
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
