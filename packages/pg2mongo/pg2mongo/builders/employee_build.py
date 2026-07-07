from __future__ import annotations

from typing import Any, Dict

from pg2mongo.builders.contacts import phones_from_legacy
from pg2mongo.builders.embedded import address_from_row, branch_dto


def build_employee_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Postgres employee row into the API-shaped ``employees`` document."""
    address = address_from_row(row)

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("name") or "",
        "title": row.get("title") or "",
        "department": row.get("department") or "",
        "phones": phones_from_legacy(
            row.get("phone1"),
            row.get("phone2"),
            primary_type="mobile",
            secondary_type="business",
        ),
        "email": row.get("email") or "",
        "active": True,
        "address": address,
    }

    branch_id = row.get("branch_id")
    if branch_id:
        doc["branch"] = branch_dto(branch_id, code=row.get("branch_code") or "")

    return doc
