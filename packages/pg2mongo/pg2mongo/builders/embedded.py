from __future__ import annotations

from typing import Any, Mapping

from pg2mongo.builders.contacts import (
    normalize_address_fields,
    phones_from_legacy,
)
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
    """core.BranchDTO — bson ``_id``, ``name``, ``code``."""
    ref: dict[str, Any] = {"_id": safe_int(branch_id)}
    if name:
        ref["name"] = name
    if code:
        ref["code"] = code
    return ref


def address_from_row(row: Mapping[str, Any], prefix: str = "address.") -> dict[str, Any]:
    """Build a singular embedded address (employees, branches, party snapshots)."""
    apt_key = f"{prefix}apt" if f"{prefix}apt" in row else f"{prefix}apartment"
    return {
        "address1": row.get(f"{prefix}address1") or "",
        "address2": row.get(f"{prefix}address2") or "",
        "apartment": row.get(apt_key) or "",
        "city": row.get(f"{prefix}city") or "",
        "state": row.get(f"{prefix}state") or "",
        "zipcode": row.get(f"{prefix}zipcode") or row.get(f"{prefix}zipCode") or "",
        "country": row.get(f"{prefix}country") or "",
    }


def user_dto(
    user_id: Any,
    *,
    name: str = "",
) -> dict[str, Any]:
    """core.UserDTO — bson ``_id``, ``name``."""
    ref: dict[str, Any] = {"_id": safe_int(user_id)}
    if name:
        ref["name"] = name
    return ref


def user_snapshot(
    user_id: Any,
    *,
    name: str = "",
    email: str = "",
) -> dict[str, Any]:
    """
    Lightweight ``core.User`` embed used on invoice employee / audit fields.

    Persists ``_id`` + ``name`` (and optional ``email``). Does not write
    ``userName`` / ``fullName`` / ``password``.
    """
    ref: dict[str, Any] = {"_id": safe_int(user_id)}
    if name:
        ref["name"] = name
    if email:
        ref["email"] = email
    return ref


def employee_dto(employee_id: Any, *, name: str = "") -> dict[str, Any]:
    """employee.EmployeeDTO — bson ``id`` (not ``_id``), ``name``."""
    ref: dict[str, Any] = {"id": safe_int(employee_id)}
    if name:
        ref["name"] = name
    return ref


# Back-compat alias used by older call sites / delivery helpers.
employee_snapshot = employee_dto


def container_snapshot(
    container_id: Any,
    *,
    name: str = "",
    container_number: str = "",
) -> dict[str, Any]:
    """core.Container embed — bson ``_id``, ``name``, ``containerNumber``."""
    ref: dict[str, Any] = {"_id": safe_int(container_id)}
    if name:
        ref["name"] = name
    if container_number:
        ref["containerNumber"] = container_number
    return ref


def delivery_snapshot(
    delivery_id: Any,
    *,
    name: str = "",
) -> dict[str, Any]:
    """core.Delivery embed — bson ``_id``, ``name``."""
    ref: dict[str, Any] = {"_id": safe_int(delivery_id)}
    if name:
        ref["name"] = name
    return ref


def customer_snapshot(
    row: Mapping[str, Any],
    prefix: str,
    *,
    default_customer_type: int,
    primary_phone_type: str = "mobile",
    secondary_phone_type: str = "home",
) -> dict[str, Any] | None:
    """
    core.CustomerParty snapshot for pickups/invoices.

    Writes singular ``address`` only. Omits party ``_id`` (ObjectId is resolved
    by the API when known; numeric Postgres ids must not be stored as ``_id``).
    """
    party_id = safe_int(row.get(f"{prefix}.id"), default=-1)
    if party_id <= 0:
        return None

    cus_type = row.get(f"{prefix}.cus_type")
    customer_type = (
        mongo_customer_type(cus_type, default=default_customer_type)
        if cus_type is not None
        else default_customer_type
    )

    phones = phones_from_legacy(
        row.get(f"{prefix}.phone1"),
        row.get(f"{prefix}.phone2"),
        primary_type=primary_phone_type,
        secondary_type=secondary_phone_type,
    )
    address = normalize_address_fields(
        address_from_row(row, prefix=f"{prefix}.address.")
    )

    doc: dict[str, Any] = {
        "name": row.get(f"{prefix}.name") or "",
        "customerType": customer_type,
        "phones": phones,
        "email": row.get(f"{prefix}.email") or "",
        "IDNumber": row.get(f"{prefix}.id_number") or "",
    }

    if any(address.values()):
        doc["address"] = address

    return doc
