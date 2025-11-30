from __future__ import annotations
from typing import Any, Dict, Iterable, Tuple, List
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING, UpdateOne
from pymongo.collection import Collection


def get_collection(client, db: str, coll: str) -> Collection:
    return client[db][coll]


def ensure_indexes(collection: Collection, upsert_key: str) -> None:
    collection.create_index([(upsert_key, ASCENDING)], unique=True, name=f"uniq_{upsert_key}")
    collection.create_index([("number", ASCENDING)], name="idx_number")
    collection.create_index([("updatedAt", DESCENDING)], name="idx_updatedAt")
    collection.create_index([("createdAt", DESCENDING)], name="idx_createdAt")


def get_last_processed_timestamp(collection: Collection) -> str | None:
    """
    Get the most recent timestamp from the collection, preferring updatedAt then createdAt.
    Returns an ISO-like string suitable for the Postgres query window, or None if empty.
    """
    doc = collection.find_one(
        filter={},
        projection={"_id": 0, "updatedAt": 1, "createdAt": 1},
        sort=[("updatedAt", DESCENDING), ("createdAt", DESCENDING)],
    )
    if not doc:
        return None
    ts = doc.get("updatedAt") or doc.get("createdAt")
    return ts.isoformat() if ts else None


def upsert_one(collection: Collection, doc: Dict[str, Any], upsert_key: str) -> None:
    """
    Single-document upsert (kept for completeness; bulk_upsert_docs is preferred).
    """
    key_val = doc.get(upsert_key)
    if key_val is None:
        return
    now = datetime.now(timezone.utc)
    collection.update_one(
        {upsert_key: key_val},
        {
            "$set": {**doc, "updatedAt": doc.get("updatedAt") or now},
            "$setOnInsert": {"createdAt": doc.get("createdAt") or now},
        },
        upsert=True,
    )


def bulk_upsert_docs(
    collection: Collection,
    docs: Iterable[Dict[str, Any]],
    *,
    upsert_key: str,
    ordered: bool = False,
) -> Tuple[int, int, int]:
    """
    High-performance batch upsert using UpdateOne ops.
    Returns (matched_count, modified_count, upserted_count).
    """
    now = datetime.now(timezone.utc)
    ops: List[UpdateOne] = []
    for d in docs:
        key_val = d.get(upsert_key)
        if key_val is None:
            continue
        ops.append(
            UpdateOne(
                {upsert_key: key_val},
                {
                    "$set": {**d, "updatedAt": d.get("updatedAt") or now},
                    "$setOnInsert": {"createdAt": d.get("createdAt") or now},
                },
                upsert=True,
            )
        )
    if not ops:
        return (0, 0, 0)

    res = collection.bulk_write(ops, ordered=ordered, bypass_document_validation=True)
    matched = getattr(res, "matched_count", 0)
    modified = getattr(res, "modified_count", 0)
    upserted = len(getattr(res, "upserted_ids", {}) or {})
    return (matched, modified, upserted)
