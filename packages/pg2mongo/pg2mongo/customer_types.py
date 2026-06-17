from __future__ import annotations

from typing import Any

SENDER = 1
RECEIVER = 2

POSTGRES_TO_MONGO_CUSTOMER_TYPE = {
    0: SENDER,
    1: RECEIVER,
}


def mongo_customer_type(value: Any, *, default: int = SENDER) -> int:
    """Map Postgres cus_type values to Mongo customerType enum values."""
    try:
        pg_value = int(value)
    except (TypeError, ValueError):
        return default
    return POSTGRES_TO_MONGO_CUSTOMER_TYPE.get(pg_value, default)
