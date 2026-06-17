from __future__ import annotations

from typing import Dict, Any

from pg2mongo import collections as cols
from pg2mongo.utils import to_utc, decimal_to_float


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        parsed = int(value)
    except Exception:
        return None
    return parsed if parsed > 0 else None


def _ref_with_id(value: Any, **extra: Any) -> Dict[str, Any]:
    ref: Dict[str, Any] = {}
    parsed_id = _safe_int(value)
    if parsed_id is not None:
        ref["id"] = parsed_id
    for key, val in extra.items():
        if val not in (None, ""):
            ref[key] = val
    return ref


def _phone_doc(phone_type: str, number: str, *, is_primary: bool = False) -> Dict[str, Any]:
    phone: Dict[str, Any] = {"type": phone_type, "number": number}
    if is_primary:
        phone["isPrimary"] = True
    return phone


def _party_doc(row: Dict[str, Any], prefix: str, primary_phone_type: str) -> Dict[str, Any] | None:
    party_id = _safe_int(row.get(f"{prefix}.id"))
    if party_id is None:
        return None

    phone1 = row.get(f"{prefix}.phone1") or ""
    phone2 = row.get(f"{prefix}.phone2") or ""
    phones = []
    if phone1:
        phones.append(_phone_doc(primary_phone_type, phone1, is_primary=True))
    if phone2:
        phones.append(_phone_doc("business", phone2))

    party: Dict[str, Any] = {
        "id": party_id,
        "name": row.get(f"{prefix}.name") or "",
        "customerType": int(row.get(f"{prefix}.cus_type") or 0),
        "phones": phones,
        "IDNumber": row.get(f"{prefix}.id_number") or "",
        "address": {
            "city": row.get(f"{prefix}.address.city") or "",
            "state": row.get(f"{prefix}.address.state") or "",
            "zipcode": row.get(f"{prefix}.address.zipcode") or "",
        },
    }

    address1 = row.get(f"{prefix}.address.address1") or ""
    country = row.get(f"{prefix}.address.country") or ""
    if address1:
        party["address"]["address1"] = address1
    if country:
        party["address"]["country"] = country

    branch = _ref_with_id(row.get(f"{prefix}.branch_id"))
    if branch:
        party["branch"] = branch

    return party


def build_invoice_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Mongo invoice document from a vwinvoice_api row.
    """
    doc: Dict[str, Any] = {
        "oldID": int(row["id"]),
        "number": row.get("number") or "",
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
        "date": to_utc(row.get("invoice_date")),
        "paidRegion": row.get("paid_region") or "",
        "paidStatus": row.get("paid_status") or "",
        "branch": _ref_with_id(
            row.get("branch_id"),
            code=row.get("branch_code") or "",
        ),
        "cost": decimal_to_float(row.get("cost")),
        "employee": _ref_with_id(
            row.get("driver_id") or row.get("user_id"),
            name=row.get("driver.name") or "",
            userName=row.get("user.name") or "",
            fullName=row.get("driver.name") or row.get("user.name") or "",
        ),
        "container": _ref_with_id(
            row.get("container_id"),
            name=row.get("container_designation") or "",
        ),
        "discount": decimal_to_float(row.get("discount") or 0),
        "payment": decimal_to_float(row.get("payment") or 0),
        "balance": decimal_to_float(row.get("balance") or 0),
        "surcharge": decimal_to_float(row.get("recharge") or 0),
        cols.INVOICE_DETAILS_FIELD: [],
    }

    sender = _party_doc(row, "sender", "business")
    if sender:
        doc["sender"] = sender

    receiver = _party_doc(row, "receiver", "mobile")
    if receiver:
        doc["receiver"] = receiver

    return doc
