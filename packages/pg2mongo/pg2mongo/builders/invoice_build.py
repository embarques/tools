from __future__ import annotations

from typing import Dict, Any

from pg2mongo import collections as cols
from pg2mongo.builders.embedded import (
    branch_dto,
    container_snapshot,
    customer_snapshot,
    user_snapshot,
)
from pg2mongo.customer_types import RECEIVER, SENDER
from pg2mongo.utils import to_utc, decimal_to_float


def build_invoice_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Mongo invoice document from a vwinvoice_api row."""
    doc: Dict[str, Any] = {
        "oldID": int(row["id"]),
        "number": row.get("number") or "",
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
        "date": to_utc(row.get("invoice_date")),
        "isVoid": bool(row.get("is_void", False)),
        "isArchive": bool(row.get("is_archive", False)),
        "registration": row.get("registration") or "",
        "paidRegion": row.get("paid_region") or "",
        "paidStatus": row.get("paid_status") or "",
        "branch": branch_dto(
            row.get("branch_id"),
            code=row.get("branch_code") or "",
        ),
        "cost": decimal_to_float(row.get("cost")),
        "user": user_snapshot(
            row.get("user_id"),
            userName=row.get("user.name") or "",
            fullName=row.get("user.name") or "",
        ),
        "employee": user_snapshot(
            row.get("driver_id"),
            name=row.get("driver.name") or "",
            fullName=row.get("driver.name") or "",
        ),
        "container": container_snapshot(
            row.get("container_id"),
            name=row.get("container_designation") or "",
        ),
        "discount": decimal_to_float(row.get("discount") or 0),
        "payment": decimal_to_float(row.get("payment") or 0),
        "balance": decimal_to_float(row.get("balance") or 0),
        "surcharge": decimal_to_float(row.get("recharge") or 0),
        cols.INVOICE_DETAILS_FIELD: [],
    }

    sender = customer_snapshot(row, "sender", default_customer_type=SENDER)
    if sender:
        doc["sender"] = sender

    receiver = customer_snapshot(row, "receiver", default_customer_type=RECEIVER)
    if receiver:
        doc["receiver"] = receiver

    return doc
