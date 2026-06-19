from __future__ import annotations

import re
from typing import Any


def normalize_phone_number(number: Any) -> str:
    """Normalize common NANP phone values to E.164 (+1XXXXXXXXXX)."""
    if number is None:
        return ""

    raw = str(number).strip()
    if not raw:
        return ""

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if raw.startswith("+") and digits:
        return f"+{digits}"
    return digits or raw


def phone_doc(phone_type: str, number: Any, *, is_primary: bool = False) -> dict[str, Any]:
    phone: dict[str, Any] = {
        "type": phone_type,
        "number": normalize_phone_number(number),
    }
    if is_primary:
        phone["isPrimary"] = True
    return phone
