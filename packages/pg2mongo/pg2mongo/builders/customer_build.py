from __future__ import annotations

from typing import Dict, Any

from pg2mongo.builders.contacts import (
    customer_addresses_from_legacy,
    phones_from_legacy,
    primary_phone_number,
)
from pg2mongo.builders.embedded import address_from_row, branch_dto
from pg2mongo.customer_types import mongo_customer_type
from pg2mongo.utils import to_utc


def build_customer_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Postgres row from vwcustomer_api to the API-shaped ``customers`` document."""
    created_at = to_utc(row.get("time_created"))
    updated_at = to_utc(row.get("time_modified") or row.get("time_created"))

    phones = phones_from_legacy(
        row.get("phone1"),
        row.get("phone2"),
        primary_type="mobile",
        secondary_type="business",
    )
    legacy_address = address_from_row(row)
    addresses = customer_addresses_from_legacy(
        legacy_address,
        primary_phone=primary_phone_number(phones),
    )

    doc: Dict[str, Any] = {
        "name": row.get("name") or "",
        "customerType": mongo_customer_type(row.get("cus_type")),
        "phones": phones,
        "addresses": addresses,
        "email": row.get("email") or "",
        "active": bool(row.get("active", True)),
        "IDNumber": row.get("id_number") or "",
        "createdAt": created_at,
        "updatedAt": updated_at,
        "notes": row.get("notes") or "",
        "accountBalance": 0,
        "branch": branch_dto(
            row.get("branch_id"),
            name=row.get("branch_name") or "",
            code=row.get("branch_code") or "",
        ),
        "receivers": [],
    }
    return doc
