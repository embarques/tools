from __future__ import annotations

from typing import Dict, Any

from pg2mongo.utils import to_utc


def build_pickup_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the pickup Mongo doc, matching the shape you described.
    """
    doc: Dict[str, Any] = {
        "oldID": int(row["id"]),
        "date": to_utc(row.get("pickup_date")),
        "createdAt": to_utc(row.get("pickup_created")),
        "updatedAt": to_utc(row.get("pickup_modified")),
        "completed": bool(row.get("completed", False)),
        "user": {
            "_id": int(row.get("user.id") or 0),
            "name": row.get("user.name") or "",
        },
        "branch": {
            "_id": int(row.get("branch.id") or 0),
            "code": row.get("branch.code") or "",
        },
        "employee": {},  # You can fill in details if needed
        "purpose": row.get("purpose") or "",
        "comments": [],
        "sector": {
            "_id": int(row.get("sector_id") or 0),
            "name": row.get("sector_name") or "",
        },
    }

    # Sender
    sender_id = row.get("sender.id")
    if sender_id:
        doc["sender"] = {
            "_id": None,  # link to customer ObjectId if you want later
            "oldID": int(sender_id),
            "name": row.get("sender.name") or "",
            "customerType": 1,
            "phone1": row.get("sender.phone1") or "",
            "address": {
                "address1": row.get("sender.address.address1") or "",
                "city": row.get("sender.address.city") or "",
                "state": row.get("sender.address.state") or "",
                "zipcode": row.get("sender.address.zipcode") or "",
                "country": row.get("sender.address.country") or "",
            },
        }

    # Comments
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


def format_pickup_verbose(doc: dict, *, action: str) -> str:
    """One-line summary for verbose pickup transfer output."""
    pickup_id = doc.get("_id", doc.get("oldID"))
    sender = doc.get("sender") or {}
    address = sender.get("address") or {}
    name = sender.get("name") or ""
    phone = sender.get("phone1") or ""
    city = address.get("city") or ""
    date_str = format_pickup_date(doc.get("date"))
    return (
        f"[pickup] {action} id={pickup_id} name={name} "
        f"tel={phone} city={city} date={date_str}"
    )
