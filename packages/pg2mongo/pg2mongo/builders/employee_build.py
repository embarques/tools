from __future__ import annotations

from typing import Any, Dict

from pg2mongo.phones import phone_doc


def build_employee_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres employee row into the current MongoDB employee document.
    """
    address = {
        "city": row.get("address.city") or "",
        "state": row.get("address.state") or "",
        "zipcode": row.get("address.zipcode") or "",
    }

    phone1 = row.get("phone1") or ""

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("name") or "",
        "title": row.get("title") or "",
        "department": row.get("department") or "",
        "phones": [phone_doc("mobile", phone1, is_primary=True)] if phone1 else [],
        "email": row.get("email") or "",
        "active": True,  # default; change if you add an active field in SQL
        "address": address,
    }

    branch_id = row.get("branch_id")
    if branch_id:
        doc["branch"] = {
            "id": int(branch_id),
            "code": row.get("branch_code") or "",
        }

    # You have User* in the Go model, but the query doesn’t return user info yet.
    # When you add user_id or similar, you can extend this part.
    # doc["user"] = {...}

    return doc
