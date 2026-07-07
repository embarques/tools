from __future__ import annotations

from typing import Any, Dict

from pg2mongo.builders.contacts import phones_from_legacy
from pg2mongo.builders.embedded import address_from_row


def build_branch_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Postgres branch row into the API-shaped ``branches`` document."""
    address = address_from_row(row)
    if not address.get("address1"):
        address["address1"] = row.get("address.address1") or ""

    settings: Dict[str, Any] = {
        "labelPrefix": row.get("prefix") or "",
        "invoiceCreatedThruIncomeStatement": False,
        "printLabelCount": True,
        "roundDecimalPlaces": 2,
        "defaultLabelStatus": int(row.get("default_label_status") or 0),
    }

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("name") or "",
        "type": row.get("b_type") or "",
        "code": row.get("code") or "",
        "phones": phones_from_legacy(
            row.get("phone1"),
            row.get("phone2"),
            primary_type="business",
            secondary_type="business",
        ),
        "disclaimer": row.get("disclaimer") or "",
        "logo": row.get("logo") or "",
        "address": address,
        "settings": settings,
    }

    return doc
