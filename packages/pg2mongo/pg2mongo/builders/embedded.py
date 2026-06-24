from __future__ import annotations

from typing import Any, Mapping

from pg2mongo.customer_types import mongo_customer_type


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def branch_dto(
    branch_id: Any,
    *,
    name: str = "",
    code: str = "",
) -> dict[str, Any]:
    ref: dict[str, Any] = {"_id": safe_int(branch_id)}
    if name:
        ref["name"] = name
    if code:
        ref["code"] = code
    return ref


def address_from_row(row: Mapping[str, Any], prefix: str = "address.") -> dict[str, Any]:
    """Build an embedded Address from flattened Postgres/view columns."""
    apt_key = f"{prefix}apt" if f"{prefix}apt" in row else f"{prefix}apartment"
    return {
        "address1": row.get(f"{prefix}address1") or "",
        "address2": row.get(f"{prefix}address2") or "",
        "apartment": row.get(apt_key) or "",
        "city": row.get(f"{prefix}city") or "",
        "state": row.get(f"{prefix}state") or "",
        "zipcode": row.get(f"{prefix}zipcode") or "",
        "country": row.get(f"{prefix}country") or "",
    }


def user_snapshot(
    user_id: Any,
    *,
    name: str = "",
    userName: str = "",
    fullName: str = "",
    email: str = "",
) -> dict[str, Any]:
    ref: dict[str, Any] = {"_id": safe_int(user_id)}
    if name:
        ref["name"] = name
    if userName:
        ref["userName"] = userName
    if fullName:
        ref["fullName"] = fullName
    elif name:
        ref["fullName"] = name
    if email:
        ref["email"] = email
    return ref


def employee_snapshot(employee_id: Any, *, name: str = "") -> dict[str, Any]:
    ref: dict[str, Any] = {"_id": safe_int(employee_id)}
    if name:
        ref["name"] = name
    return ref


def container_snapshot(
    container_id: Any,
    *,
    name: str = "",
    container_number: str = "",
) -> dict[str, Any]:
    ref: dict[str, Any] = {"_id": safe_int(container_id)}
    if name:
        ref["name"] = name
    if container_number:
        ref["containerNumber"] = container_number
    return ref


def customer_snapshot(
    row: Mapping[str, Any],
    prefix: str,
    *,
    default_customer_type: int,
) -> dict[str, Any] | None:
    """Embedded Customer snapshot (pickups, invoices)."""
    party_id = safe_int(row.get(f"{prefix}.id"), default=-1)
    if party_id <= 0:
        return None

    cus_type = row.get(f"{prefix}.cus_type")
    customer_type = (
        mongo_customer_type(cus_type, default=default_customer_type)
        if cus_type is not None
        else default_customer_type
    )

    doc: dict[str, Any] = {
        "oldID": party_id,
        "name": row.get(f"{prefix}.name") or "",
        "customerType": customer_type,
        "phone1": row.get(f"{prefix}.phone1") or "",
        "phone2": row.get(f"{prefix}.phone2") or "",
        "email": row.get(f"{prefix}.email") or "",
        "IDNumber": row.get(f"{prefix}.id_number") or "",
        "active": True,
        "address": address_from_row(row, prefix=f"{prefix}.address."),
    }

    branch_id = safe_int(row.get(f"{prefix}.branch_id"), default=0)
    if branch_id > 0:
        doc["branch"] = branch_dto(branch_id)

    return doc
