# invoice_detail_build.py
#
# Helpers to:
#   - Load invoice details + barcodes from Postgres (vwinvoice_details_api)
#   - Insert them into MongoDB (invoice_details collection)
#   - Link them back to the parent invoice document (invoices.invoiceDetails)

from datetime import datetime, timezone
from typing import List, Dict, Any

import click
from bson.objectid import ObjectId

from pg2mongo import collections as cols
from pg2mongo.utils import to_float, pg_row_to_dict


def _safe_int(value) -> int:
    """
    Convert value to int. Return 0 for None or invalid values.
    This keeps the rest of the code simple and protects against
    weird strings like 'id', 'barcode.gen_num', etc.
    """
    try:
        if value is None:
            return 0
        return int(value)
    except Exception:
        return 0


# ----------------------------------------------------------------------
#  BUILDERS
# ----------------------------------------------------------------------


def build_invoice_detail_doc(detail_id: int, rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a clean invoice detail MongoDB document from a Postgres row dict.
    """
    now = datetime.now(timezone.utc)

    doc: Dict[str, Any] = {
        "_id": ObjectId(),
        "oldID": detail_id,
        "name": rec.get("description"),
        "quantity": rec.get("quantity"),
        "labels": rec.get("labels"),
        "price": to_float(rec.get("price")),
        "total": to_float(rec.get("amount")),
        "createdAt": now,
        "updatedAt": now,
        "barcodes": [],
    }

    return doc


def build_barcode_doc(rec: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Build a clean barcode subdocument from a Postgres row dict.

    Returns:
        - dict when there is a valid barcode
        - None when there is no real barcode (e.g. empty or header).
    """
    number = rec.get("barcode.number")

    # Skip bogus/header barcode values
    if not number or number == "barcode.number":
        return None

    barcode: Dict[str, Any] = {
        "number": number,
    }

    # gen_num / id → barcode _id (column name varies by Postgres view version)
    gen_id = _safe_int(rec.get("barcode.gen_num") or rec.get("barcode.id"))
    if gen_id > 0:
        barcode["id"] = gen_id

    # scanDate: only accept real datetime, not a literal string
    scan_date = rec.get("barcode.scandate")
    if isinstance(scan_date, datetime):
        barcode["scanDate"] = scan_date

    # status
    status_id = _safe_int(rec.get("barcode.status_id"))
    if status_id > 0:
        barcode["status"] = {
            "id": status_id,
            "name": rec.get("barcode.status_name") or "",
        }

    # container
    container_id = _safe_int(rec.get("barcode.container_id"))
    if container_id > 0:
        barcode["container"] = {
            "id": container_id,
            "name": rec.get("barcode.container_name") or "",
        }

    # delivery
    delivery_id = _safe_int(rec.get("barcode.delivery_id"))
    if delivery_id > 0:
        barcode["delivery"] = {
            "id": delivery_id,
            "name": rec.get("barcode.delivery_name") or "",
        }

    return barcode


# ----------------------------------------------------------------------
#  LOAD FROM POSTGRES
# ----------------------------------------------------------------------


def load_invoice_details(
    pg_conn,
    invoice_old_id: int,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Load invoice details + barcodes for a given invoice_old_id from Postgres.

    Source:
        vwinvoice_details_api

    Each row may represent:
        - one invoice detail line, and
        - zero or one barcode attached to that detail.

    We group by detail_id so the result is:
        [
          {
            _id: ObjectId(...),
            oldID: <detail_id>,
            name: ...,
            quantity: ...,
            price: ...,
            total: ...,
            barcodes: [ {...}, {...}, ... ]
          },
          ...
        ]
    """

    sql = """
        SELECT
            id,
            quantity,
            labels,
            description,
            price,
            amount,
            invoice_id,
            "barcode.number",
            "barcode.container_id",
            "barcode.container_name",
            "barcode.delivery_id",
            "barcode.delivery_name",
            "barcode.status_id",
            "barcode.status_name",
            "barcode.invoice_detail_id",
            "barcode.scandate",
            "barcode.time_modified",
            "barcode.id"
        FROM vwinvoice_details_api
        WHERE invoice_id = %s
        ORDER BY id;
    """

    if verbose:
        click.secho(
            f"[details] Loading invoice details for oldID={invoice_old_id}",
            fg="cyan",
        )

    # Map detail_id -> detail doc so we can aggregate barcodes
    details: Dict[int, Dict[str, Any]] = {}

    # New cursor just for this query; col_names bound to this SELECT
    with pg_conn.cursor() as cur:
        cur.execute(sql, (invoice_old_id,))

        # Column names so we can map row → dict
        col_names = [desc[0] for desc in cur.description]

        for row in cur:
            rec = pg_row_to_dict(row, col_names)

            # Convert id to int; header rows ("id") become 0 and are skipped
            detail_id = _safe_int(rec.get("id"))

            # If we can't get a valid numeric id, treat this row as junk/header
            if detail_id == 0:
                if verbose:
                    click.secho(
                        f"[details] Skipping row with invalid id={rec.get('id')!r}",
                        fg="yellow",
                    )
                continue

            # Create the base detail doc once per detail_id
            if detail_id not in details:
                details[detail_id] = build_invoice_detail_doc(detail_id, rec)

            # Build barcode (optional) and append if valid
            barcode = build_barcode_doc(rec)
            if barcode is not None:
                details[detail_id]["barcodes"].append(barcode)

    detail_list = list(details.values())

    if verbose:
        barcode_count = sum(len(d["barcodes"]) for d in detail_list)
        click.secho(
            f"[details] Loaded {len(detail_list)} detail(s) and "
            f"{barcode_count} barcode(s) for oldID={invoice_old_id}",
            fg="cyan",
        )

    return detail_list


# ----------------------------------------------------------------------
#  INSERT INTO MONGO & LINK TO INVOICE
# ----------------------------------------------------------------------


def add_invoice_details(
    pg_conn,
    mongo_client,
    mongo_db_name: str,
    invoice_old_id: int,
    invoice_id: ObjectId,
    session=None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """
    Add invoice details (and nested barcodes) for a single invoice into MongoDB.

    Steps:
      1. Load invoice details + barcodes from Postgres.
      2. Attach invoice reference (Mongo id + oldID) to each detail.
      3. Insert detail documents into invoice_details collection.
      4. Update the invoice document with an array of detail references.

    All Mongo writes accept an optional `session` so they can participate in
    a transaction started at the invoice level.
    """

    db = mongo_client[mongo_db_name]
    inv_collection = db[cols.INVOICES]
    inv_details_collection = db[cols.INVOICE_DETAILS]

    # 1) Load detail docs from Postgres
    details = load_invoice_details(pg_conn, invoice_old_id, verbose=verbose)

    # Remove previously synced details so re-runs replace rather than duplicate
    inv_details_collection.delete_many(
        {"$or": [{"invoice.id": invoice_id}, {"invoice._id": invoice_id}]},
        session=session,
    )

    # If no details, still ensure invoice has an empty array
    if not details:
        if verbose:
            click.secho(
                f"[details] No details found for oldID={invoice_old_id}; "
                f"setting {cols.INVOICES}.{cols.INVOICE_DETAILS_FIELD} = [].",
                fg="yellow",
            )

        inv_collection.update_one(
            {"_id": invoice_id},
            {"$set": {cols.INVOICE_DETAILS_FIELD: []}},
            session=session,
        )
        return []

    # 2) Attach invoice reference to each detail
    for d in details:
        d["invoice"] = {
            "id": invoice_id,
            "oldID": invoice_old_id,
        }

    if verbose:
        click.secho(
            f"[details] Inserting {len(details)} detail(s) into "
            f"{cols.qualified(mongo_db_name, cols.INVOICE_DETAILS)} for oldID={invoice_old_id}",
            fg="blue",
        )

    # 3) Insert details into invoice_details collection
    insert_result = inv_details_collection.insert_many(
        details,
        session=session,
    )

    # 4) Build reference list and update parent invoice
    inv_details_refs: List[Dict[str, Any]] = [
        {"id": str(oid)} for oid in insert_result.inserted_ids
    ]

    inv_collection.update_one(
        {"_id": invoice_id},
        {"$set": {cols.INVOICE_DETAILS_FIELD: inv_details_refs}},
        session=session,
    )

    if verbose:
        click.secho(
            f"[details] Updated {cols.qualified(mongo_db_name, cols.INVOICES)} with "
            f"{len(inv_details_refs)} {cols.INVOICE_DETAILS_FIELD} reference(s)",
            fg="green",
        )

    return inv_details_refs
