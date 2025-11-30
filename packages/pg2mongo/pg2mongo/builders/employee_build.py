from __future__ import annotations

from typing import Any, Dict


def build_employee_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres employee row into the MongoDB employee document.

    Expected row keys from SQL:
      id, name, title, department,
      address.address1, address.city, address.zipcode, address.country,
      phone1, email, branch_id
    """
    address = {
        "address1": row.get("address.address1") or "",
        "city": row.get("address.city") or "",
        "zipcode": row.get("address.zipcode") or "",
        "country": row.get("address.country") or "",
    }

    # Remove empty address fields if you want it cleaner
    address = {k: v for k, v in address.items() if v}

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("name") or "",
        "title": row.get("title") or "",
        "department": row.get("department") or "",
        "phone1": row.get("phone1") or "",
        "phone2": "",  # not in query; you can map later if you add it
        "email": row.get("email") or "",
        "active": True,  # default; change if you add an active field in SQL
        "address": address or None,
    }

    branch_id = row.get("branch_id")
    if branch_id:
        doc["branch"] = {"_id": branch_id}

    # You have User* in the Go model, but the query doesn’t return user info yet.
    # When you add user_id or similar, you can extend this part.
    # doc["user"] = {...}

    return doc
