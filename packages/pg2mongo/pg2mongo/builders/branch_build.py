from __future__ import annotations

from typing import Any, Dict

from pg2mongo.phones import phone_doc


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
        "city": row.get("address.city") or "",
        "state": row.get("address.state") or "",
        "zipcode": row.get("address.zipcode") or "",
        "country": row.get("address.country") or "",
    }

    settings: Dict[str, Any] = {
        "labelPrefix": row.get("prefix") or "",
        "roundDecimalPlaces": 2,
        "defaultLabelStatus": row.get("default_label_status") or 0,
    }

    phones = []
    phone1 = row.get("phone1") or ""
    phone2 = row.get("phone2") or ""
    if phone1:
        phones.append(phone_doc("business", phone1, is_primary=True))
    if phone2:
        phones.append(phone_doc("business", phone2))

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("name") or "",
        "type": row.get("b_type") or "",
        "code": row.get("code") or "",
        "phones": phones,
        "disclaimer": row.get("disclaimer") or "",
        "logo": row.get("logo") or "",
        "address": address,
        "settings": settings,
    }

    return doc
