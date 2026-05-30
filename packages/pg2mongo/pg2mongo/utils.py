from __future__ import annotations

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from pg2mongo import collections as cols

from pymongo.database import Database


def to_utc(value: Any | None) -> Optional[datetime]:
    """
    Normalize date/datetime values to timezone-aware UTC datetimes.

    Accepts:
    - datetime (naive or aware)
    - date (converted to midnight UTC)
    - None → None
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, date):
        # Convert date → datetime at midnight UTC
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)

    raise TypeError(f"Unsupported date/datetime type: {type(value)!r}")


def decimal_to_float(value: Any) -> Any:
    """
    Convert Decimal to float; leave other types untouched.
    """
    if isinstance(value, Decimal):
        return float(value)
    return value

def to_float(value):
    """
    Safely convert Postgres numeric fields to float.
    Strings or None become 0.0. Decimal becomes float.
    """
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def pg_row_to_dict(row: Any, col_names: Sequence[str] | None = None) -> dict[str, Any]:
    """
    Normalize a psycopg row to a plain dict.

    When the connection uses ``dict_row``, *row* is already a mapping and must
    be returned as-is.  Tuple rows are zipped with *col_names*.
    """
    if isinstance(row, Mapping):
        return dict(row)
    if col_names is None:
        raise ValueError("col_names required when row is not a mapping")
    return dict(zip(col_names, row))


# ------------------------------
# Mongo helpers (from mongo_utils)
# ------------------------------


def create_unique_index(database: Database, collection_name: str, keys: dict) -> None:
    """
    Create a unique index on the given collection.

    Example:
        create_unique_index(db, "customers", {"name": 1, "phone1": 1})
    """
    coll = database[collection_name]
    coll.create_index(list(keys.items()), unique=True)


from pg2mongo.sequences import get_next_sequence  # noqa: F401 — re-export
