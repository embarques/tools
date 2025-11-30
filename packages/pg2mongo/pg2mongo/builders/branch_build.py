from __future__ import annotations

from typing import Any, Dict


def build_branch_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres branch row into the MongoDB branch document.

    Expected row keys from SQL:
      id, name, code, b_type,
      address.address1, address.address2, address.city,
      address.zipcode, address.country,
      phone1, phone2, disclaimer,
      prefix, logo, default_label_status
    """

    address = {
        "address1": row.get("address.address1") or "",
        "address2": row.get("address.address2") or "",
        "city": row.get("address.city") or "",
        "zipcode": row.get("address.zipcode") or "",
        "country": row.get("address.country") or "",
    }
    # strip empty fields
    address = {k: v for k, v in address.items() if v}

    settings: Dict[str, Any] = {
        "labelPrefix": row.get("prefix") or "",
        # Defaults; you can wire these later from DB if you add columns
        "invoiceCreatedThruIncomeStatement": False,
        "printLabelCount": False,
        "roundDecimalPlaces": 2,
        "defaultLabelStatus": row.get("default_label_status") or 0,
    }

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("name") or "",
        "type": row.get("b_type") or "",
        "code": row.get("code") or "",
        "address": address or None,
        "phone1": row.get("phone1") or "",
        "phone2": row.get("phone2") or "",
        "disclaimer": row.get("disclaimer") or "",
        "logo": row.get("logo") or "",
        "settings": settings,
        "created": None,  # not coming from query; can be wired later
    }

    return doc
