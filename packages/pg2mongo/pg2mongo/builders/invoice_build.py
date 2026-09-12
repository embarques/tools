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


def _normalize_registration(raw: Any) -> str:
    value = str(raw or "").strip().upper()
    if value in {"PENDING", "COMPLETED"}:
        return value
    return value


def build_invoice_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Mongo invoice document matching ``internal/invoice.Invoice``."""
    doc: Dict[str, Any] = {
        "number": row.get("number") or "",
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
        "date": to_utc(row.get("invoice_date")),
        "isVoid": bool(row.get("is_void", False)),
        "isArchive": bool(row.get("is_archive", False)),
        "registration": _normalize_registration(row.get("registration")),
        "paidRegion": row.get("paid_region") or "",
        "paidStatus": row.get("paid_status") or "",
        "branch": branch_dto(
            row.get("branch_id"),
            code=row.get("branch_code") or "",
        ),
        "cost": decimal_to_float(row.get("cost")),
        "employee": user_snapshot(
            row.get("driver_id"),
            name=row.get("driver.name") or "",
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

    # Optional createdBy from Postgres user (portal user who registered the invoice).
    created_by = user_snapshot(
        row.get("user_id"),
        name=row.get("user.name") or "",
    )
    if created_by.get("_id", 0) > 0:
        doc["createdBy"] = created_by

    sender = customer_snapshot(
        row,
        "sender",
        default_customer_type=SENDER,
        primary_phone_type="business",
        secondary_phone_type="business",
    )
    if sender:
        doc["sender"] = sender

    receiver = customer_snapshot(
        row,
        "receiver",
        default_customer_type=RECEIVER,
        primary_phone_type="mobile",
        secondary_phone_type="home",
    )
    if receiver:
        doc["receiver"] = receiver

    return doc
