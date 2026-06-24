from __future__ import annotations

from typing import Any, Dict

from pg2mongo.builders.embedded import address_from_row, branch_dto


def build_employee_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Postgres employee row into the tenant ``employees`` document."""
    address = {
        "address1": row.get("address.address1") or "",
        "address2": "",
        "apartment": "",
        "city": row.get("address.city") or "",
        "state": row.get("address.state") or "",
        "zipcode": row.get("address.zipcode") or "",
        "country": row.get("address.country") or "",
    }

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("name") or "",
        "title": row.get("title") or "",
        "department": row.get("department") or "",
        "phone1": row.get("phone1") or "",
        "phone2": row.get("phone2") or "",
        "email": row.get("email") or "",
        "active": True,
        "address": address,
    }

    branch_id = row.get("branch_id")
    if branch_id:
        doc["branch"] = branch_dto(branch_id, code=row.get("branch_code") or "")

    return doc
