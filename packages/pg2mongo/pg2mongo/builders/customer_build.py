from __future__ import annotations

from typing import Dict, Any

from pg2mongo.customer_types import mongo_customer_type
from pg2mongo.phones import phone_doc
from pg2mongo.utils import to_utc


def build_customer_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres row from vwcustomer_api to the current Mongo customer shape.
    """
    created_at = to_utc(row.get("time_created"))
    updated_at = to_utc(row.get("time_created"))  # or time_modified if you add it
    phones = []
    phone1 = row.get("phone1") or ""
    phone2 = row.get("phone2") or ""
    if phone1:
        phones.append(phone_doc("mobile", phone1, is_primary=True))
    if phone2:
        phones.append(phone_doc("business", phone2))

    doc: Dict[str, Any] = {
        "oldID": int(row["id"]),
        "name": row.get("name") or "",
        "customerType": mongo_customer_type(row.get("cus_type")),
        "phones": phones,
        "email": row.get("email") or "",
        "createdAt": created_at,
        "updatedAt": updated_at,
        "branch": {
            "id": int(row.get("branch_id") or 0),
            "code": row.get("branch_code") or "",
            "name": row.get("branch_name") or "",
        },
        "IDNumber": row.get("id_number") or "",
        "notes": row.get("notes") or "",
        "address": {
            "address1": row.get("address.address1") or "",
            "city": row.get("address.city") or "",
            "state": row.get("address.state") or "",
            "zipcode": row.get("address.zipcode") or "",
            "country": row.get("address.country") or "",
        },
        "active": bool(row.get("active", True)),
    }
    return doc
