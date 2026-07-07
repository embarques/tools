from __future__ import annotations

from typing import Any

from pg2mongo.builders.contacts import primary_phone_number


def customer_match_filter(doc: dict[str, Any]) -> dict[str, Any]:
    """Mongo filter to find a customer without storing Postgres ``oldID``."""
    filt: dict[str, Any] = {
        "name": doc.get("name") or "",
        "customerType": doc.get("customerType"),
    }
    id_number = (doc.get("IDNumber") or "").strip()
    if id_number:
        filt["IDNumber"] = id_number
        return filt

    phone = primary_phone_number(doc.get("phones") or [])
    if phone:
        filt["phones.number"] = phone
    return filt


def pickup_match_filter(doc: dict[str, Any]) -> dict[str, Any]:
    """Mongo filter to find a pickup without storing Postgres ``oldID``."""
    sender = doc.get("sender") or {}
    addresses = sender.get("addresses") or []
    address1 = ""
    for entry in addresses:
        if entry.get("isPrimary"):
            address1 = entry.get("address1") or ""
            break
    if not address1 and addresses:
        address1 = addresses[0].get("address1") or ""

    filt: dict[str, Any] = {
        "date": doc.get("date"),
        "sender.name": sender.get("name") or "",
    }
    if address1:
        filt["sender.addresses.address1"] = address1
    return filt


def invoice_match_filter(doc: dict[str, Any]) -> dict[str, Any]:
    """Mongo filter to find an invoice by business number."""
    return {"number": doc.get("number") or ""}
