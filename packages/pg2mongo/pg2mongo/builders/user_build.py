from __future__ import annotations

from typing import Any, Dict

from pymongo import UpdateOne

from pg2mongo.utils import to_utc


def build_user_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres auth_user + user_profile row into the MongoDB user document.

    Matches ``internal/user.User`` bson tags:
      _id, uid, email, name, active, branch{_id,name}, role{_id,name},
      startTime, endTime, createdAt, updatedAt

    Does not write userName, fullName, or password.
    """
    branch = None
    branch_id = row.get("branch_id") or 0
    if branch_id:
        # User.BranchRef is {_id, name} — omit code.
        branch = {"_id": int(branch_id)}
        branch_name = row.get("branch_name") or ""
        if branch_name:
            branch["name"] = branch_name

    name = (row.get("full_name") or row.get("username") or "").strip()

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "uid": row.get("uid") or "",
        "email": row.get("email") or "",
        "name": name,
        "active": bool(row.get("is_active", True)),
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_created")),
    }
    if branch:
        doc["branch"] = branch

    return doc


def user_insert_op(doc: Dict[str, Any]) -> UpdateOne:
    """
    Insert a user only when no document exists for this Postgres id.

    Existing Mongo users (e.g. Firebase accounts created in the portal) are
    left unchanged — no field updates and no deletes.
    """
    doc_id = doc["_id"]
    fields = {key: value for key, value in doc.items() if key != "_id"}
    return UpdateOne(
        {"_id": doc_id},
        {"$setOnInsert": fields},
        upsert=True,
    )
