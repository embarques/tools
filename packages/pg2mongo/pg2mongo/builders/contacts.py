from __future__ import annotations

from typing import Any, Mapping

from pg2mongo.phones import phone_doc


def phones_from_legacy(
    phone1: Any = None,
    phone2: Any = None,
    *,
    primary_type: str = "mobile",
    secondary_type: str = "home",
) -> list[dict[str, Any]]:
    """Build API-style ``phones[]`` from legacy ``phone1`` / ``phone2`` columns."""
    phones: list[dict[str, Any]] = []

    if phone1:
        phones.append(phone_doc(primary_type, phone1, is_primary=True))
    if phone2:
        phones.append(
            phone_doc(
                secondary_type,
                phone2,
                is_primary=not bool(phone1),
            )
        )

    if len(phones) == 1 and "isPrimary" not in phones[0]:
        phones[0]["isPrimary"] = True

    return phones


def primary_phone_number(phones: list[dict[str, Any]]) -> str:
    for phone in phones:
        if phone.get("isPrimary"):
            return str(phone.get("number") or "")
    if phones:
        return str(phones[0].get("number") or "")
    return ""


def normalize_address_fields(address: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize legacy address keys (apt, zipCode) to API field names."""
    apartment = address.get("apartment") or address.get("apt") or ""
    address2 = address.get("address2") or ""
    if not apartment and address2 and str(address2).lower().startswith(("apt", "suite", "unit")):
        apartment = address2

    return {
        "address1": address.get("address1") or "",
        "address2": address2,
        "apartment": apartment,
        "city": address.get("city") or "",
        "state": address.get("state") or "",
        "zipcode": address.get("zipcode") or address.get("zipCode") or "",
        "country": address.get("country") or "",
    }


def customer_address_entry(
    address: Mapping[str, Any],
    *,
    label: str = "Primary",
    is_primary: bool = True,
    active: bool = True,
    phone: str = "",
) -> dict[str, Any]:
    """One element of customer ``addresses[]``."""
    normalized = normalize_address_fields(address)
    entry: dict[str, Any] = {
        "label": label,
        "isPrimary": is_primary,
        "active": active,
        **normalized,
    }
    if phone:
        entry["phone"] = phone
    return entry


def customer_addresses_from_legacy(
    address: Mapping[str, Any],
    *,
    primary_phone: str = "",
) -> list[dict[str, Any]]:
    """Convert a legacy singular ``address`` object into ``addresses[]``."""
    normalized = normalize_address_fields(address)
    if not any(normalized.values()):
        return []
    return [
        customer_address_entry(
            normalized,
            label="Primary",
            is_primary=True,
            phone=primary_phone,
        )
    ]
