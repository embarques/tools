from __future__ import annotations

from typing import Dict, Any

from pg2mongo.customer_types import SENDER, RECEIVER, mongo_customer_type
from pg2mongo.utils import to_utc


def _phone_doc(phone_type: str, number: str, *, is_primary: bool = False) -> Dict[str, Any]:
    phone: Dict[str, Any] = {"type": phone_type, "number": number}
    if is_primary:
        phone["isPrimary"] = True
    return phone


def _party_doc(row: Dict[str, Any], prefix: str) -> Dict[str, Any] | None:
    party_id = row.get(f"{prefix}.id")
    if not party_id:
        return None

    phone1 = row.get(f"{prefix}.phone1") or ""
    phone2 = row.get(f"{prefix}.phone2") or ""
    phones = []
    if phone1:
        phones.append(_phone_doc("mobile", phone1, is_primary=True))
    if phone2:
        phones.append(_phone_doc("business", phone2))

    default_customer_type = SENDER if prefix == "sender" else RECEIVER

    customer_type = row.get(f"{prefix}.customerType")
    if customer_type is not None:
        customer_type = int(customer_type)
    else:
        customer_type = mongo_customer_type(
            row.get(f"{prefix}.cus_type"),
            default=default_customer_type,
        )

    return {
        "id": int(party_id),
        "name": row.get(f"{prefix}.name") or "",
        "customerType": customer_type,
        "phones": phones,
        "email": row.get(f"{prefix}.email") or "",
        "IDNumber": row.get(f"{prefix}.id_number") or "",
        "address": {
            "address1": row.get(f"{prefix}.address.address1") or "",
            "city": row.get(f"{prefix}.address.city") or "",
            "state": row.get(f"{prefix}.address.state") or "",
            "zipcode": row.get(f"{prefix}.address.zipcode") or "",
        },
    }


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
        "branch": {
            "id": int(row.get("branch.id") or 0),
            "code": row.get("branch.code") or "",
        },
        "employee": {
            "id": int(row.get("employee.id") or 0),
            "name": row.get("employee.name") or "",
            "phones": [],
            "active": True,
        },
        "purpose": row.get("purpose") or "",
        "comments": [],
        "sector": {
            "id": int(row.get("sector_id") or 0),
            "name": row.get("sector_name") or "",
        },
    }

    sender = _party_doc(row, "sender")
    if sender:
        doc["sender"] = sender

    receiver = _party_doc(row, "receiver")
    if receiver:
        doc["receiver"] = receiver

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
    phones = sender.get("phones") or []
    phone = phones[0].get("number", "") if phones else ""
    city = address.get("city") or ""
    date_str = format_pickup_date(doc.get("date"))
    return (
        f"[pickup] {action} id={pickup_id} name={name} "
        f"tel={phone} city={city} date={date_str}"
    )
