from __future__ import annotations

from typing import Dict, Any

from pg2mongo.builders.contacts import primary_phone_number
from pg2mongo.builders.embedded import (
    branch_dto,
    customer_snapshot,
    employee_snapshot,
    user_snapshot,
)
from pg2mongo.customer_types import RECEIVER, SENDER
from pg2mongo.utils import to_utc


def build_pickup_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Build the tenant ``pickups`` document."""
    doc: Dict[str, Any] = {
        "date": to_utc(row.get("pickup_date")),
        "createdAt": to_utc(row.get("pickup_created")),
        "updatedAt": to_utc(row.get("pickup_modified")),
        "completed": bool(row.get("completed", False)),
        "user": user_snapshot(
            row.get("user.id"),
            userName=row.get("user.name") or "",
            fullName=row.get("user.name") or "",
        ),
        "branch": branch_dto(
            row.get("branch.id"),
            code=row.get("branch.code") or "",
        ),
        "employee": employee_snapshot(
            row.get("employee.id"),
            name=row.get("employee.name") or "",
        ),
        "purpose": row.get("purpose") or "",
        "comments": [],
        "sector": {
            "id": int(row.get("sector_id") or 0),
            "name": row.get("sector_name") or "",
        },
    }

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

    comment_text = row.get("comment") or ""
    if comment_text:
        doc["comments"].append(
            {
                "purpose": "comment",
                "unit": "",
                "quantity": 0,
                "description": comment_text,
            }
        )

    return doc


def format_pickup_date(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _primary_address_city(addresses: list[dict]) -> str:
    for entry in addresses:
        if entry.get("isPrimary"):
            return entry.get("city") or ""
    if addresses:
        return addresses[0].get("city") or ""
    return ""


def format_pickup_verbose(doc: dict, *, action: str) -> str:
    """One-line summary for verbose pickup transfer output."""
    pickup_id = doc.get("_id", "?")
    sender = doc.get("sender") or {}
    name = sender.get("name") or ""
    phone = primary_phone_number(sender.get("phones") or [])
    city = _primary_address_city(sender.get("addresses") or [])
    date_str = format_pickup_date(doc.get("date"))
    return (
        f"[pickup] {action} id={pickup_id} name={name} "
        f"tel={phone} city={city} date={date_str}"
    )
