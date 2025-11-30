from __future__ import annotations

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Optional

from pymongo.database import Database
from pymongo import ReturnDocument


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


def get_next_sequence(
    database: Database,
    sequence_name: str,
    session=None,
) -> int:
    """
    Uses the `counters` collection to get the next sequence number.

    Expected document shape in `counters`:
      { _id: "pickup_id", sequenceValue: <int> }

    Raises:
      RuntimeError if the counter document is missing.
    """
    coll = database["counters"]
    doc = coll.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequenceValue": 1}},
        return_document=ReturnDocument.AFTER,
        session=session,
    )
    if not doc:
        raise RuntimeError(f"Counter '{sequence_name}' not found in 'counters' collection")
    return int(doc["sequenceValue"])
