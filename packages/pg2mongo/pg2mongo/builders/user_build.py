from __future__ import annotations

from typing import Any, Dict

from pg2mongo.utils import to_utc


def build_user_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres auth_user + user_profile row into the MongoDB user document.

    Expected row keys from SQL:
      id, username, full_name, time_created,
      register_key, temp_key, branch_id
    """
    branch_id = row.get("branch_id") or 0
    branch = None
    if branch_id:
        branch = {
            "id": int(branch_id),
            "name": row.get("branch_name") or "",
            "code": row.get("branch_code") or "",
        }

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "uid": row.get("uid") or "",
        "email": row.get("email") or "",
        "userName": row.get("username") or "",
        "fullName": row.get("full_name") or "",
        "active": bool(row.get("is_active", True)),
        "branch": branch,
        "role": None,
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_created")),
    }

    # If later you uncomment RegistrationKey fields in the Go model,
    # you can also add:
    #
    # reg_key = row.get("register_key") or ""
    # temp_key = row.get("temp_key") or ""
    # if reg_key:
    #     doc["registrationKey"] = reg_key
    # if temp_key:
    #     doc["registrationTempKey"] = temp_key

    return doc
