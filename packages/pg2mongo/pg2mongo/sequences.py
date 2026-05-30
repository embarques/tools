from __future__ import annotations

from pymongo import ReturnDocument
from pymongo.database import Database

from pg2mongo import collections as cols

# Default counter documents (sequenceValue = last issued id; next call returns +1)
COUNTER_SEEDS: list[tuple[str, int]] = [
    ("user_id", 0),
    ("container_id", 0),
    ("chart_account_id", 0),
    ("income_statement_id", 0),
    ("app_menu_id", 0),
    ("permission_id", 0),
    ("role_id", 0),
    ("invoice_description_id", 0),
    ("city_id", 0),
    ("pickup_id", 0),
    ("employee_id", 0),
    ("delivery_id", 0),
]


def _max_numeric_id(db: Database, collection: str) -> int:
    doc = db[collection].find_one(
        {"_id": {"$type": "number"}},
        sort=[("_id", -1)],
        projection={"_id": 1},
    )
    if doc and isinstance(doc.get("_id"), int):
        return int(doc["_id"])
    return 0


def _default_initial(db: Database, sequence_name: str) -> int:
    if sequence_name == "pickup_id":
        return _max_numeric_id(db, cols.PICKUPS)
    return 0


def ensure_counter(
    db: Database,
    sequence_name: str,
    *,
    initial: int | None = None,
) -> None:
    """Create a counter document if missing (does not reset existing counters)."""
    coll = db[cols.COUNTERS]
    if coll.find_one({"_id": sequence_name}, projection={"_id": 1}):
        return

    if initial is None:
        initial = _default_initial(db, sequence_name)

    coll.update_one(
        {"_id": sequence_name},
        {"$setOnInsert": {"_id": sequence_name, "sequenceValue": initial}},
        upsert=True,
    )


def ensure_counters(db: Database) -> int:
    """Ensure all known counters exist. Returns how many were newly inserted."""
    created = 0
    for name, default in COUNTER_SEEDS:
        coll = db[cols.COUNTERS]
        if coll.find_one({"_id": name}, projection={"_id": 1}):
            continue
        initial = _default_initial(db, name) if name == "pickup_id" else default
        coll.update_one(
            {"_id": name},
            {"$setOnInsert": {"_id": name, "sequenceValue": initial}},
            upsert=True,
        )
        created += 1
    return created


def get_next_sequence(
    db: Database,
    sequence_name: str,
    session=None,
) -> int:
    """Atomically increment and return the next value for *sequence_name*."""
    ensure_counter(db, sequence_name)
    coll = db[cols.COUNTERS]
    doc = coll.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequenceValue": 1}},
        return_document=ReturnDocument.AFTER,
        session=session,
    )
    if not doc:
        raise RuntimeError(f"Counter '{sequence_name}' not found in 'counters' collection")
    return int(doc["sequenceValue"])
