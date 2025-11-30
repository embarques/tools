from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from pg2mongo.utils import to_utc


def build_customer_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres row from vwcustomer_api to the target Mongo customer document shape:

    {
        "oldID": <id>,
        "name": "...",
        "customerType": 1,
        "phone1": "...",
        "phone2": "...",
        "createdAt": <datetime>,
        "branch": { "_id": 1 },
        "createdByID": 5,
        "address": {
            "address1": "...",
            "address2": "...",
            "apartment": "...",
            "city": "...",
            "state": "...",
            "zipcode": "...",
            "country": "US",
        }
    }
    """
    created_at = to_utc(row.get("time_created"))
    updated_at = to_utc(row.get("time_created"))  # or time_modified if you add it

    doc: Dict[str, Any] = {
        "oldID": int(row["id"]),
        "name": row.get("name") or "",
        "customerType": int(row.get("cus_type", 0)),
        "phone1": row.get("phone1") or "",
        "phone2": row.get("phone2") or "",
        "createdAt": created_at,
        "updatedAt": updated_at,
        "branch": {
            "_id": int(row.get("branch_id") or 0),
        },
        "createdByID": int(row.get("created_by_id") or 0),
        "address": {
            "address1": row.get("address.address1") or "",
            "address2": row.get("address.address2") or "",
            "apartment": row.get("address.apt") or "",
            "city": row.get("address.city") or "",
            "state": row.get("address.state") or "",
            "zipcode": row.get("address.zipcode") or "",
            "country": row.get("address.country") or "",
        },
        "active": bool(row.get("active", True)),
    }
    return doc
