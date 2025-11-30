from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from bson.decimal128 import Decimal128
from bson import ObjectId


def to_utc(dt) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    return None


def date_only_utc(dt) -> Optional[datetime]:
    u = to_utc(dt)
    if not u:
        return None
    return u.replace(hour=0, minute=0, second=0, microsecond=0)


def convert_decimals(v: Any) -> Any:
    if isinstance(v, Decimal):
        return Decimal128(v)
    if isinstance(v, dict):
        return {k: convert_decimals(x) for k, x in v.items()}
    if isinstance(v, list):
        return [convert_decimals(x) for x in v]
    return v


def prune_empty(v: Any) -> Any:
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            px = prune_empty(x)
            if px in ("", None):
                continue
            out[k] = px
        return out
    if isinstance(v, list):
        return [px for px in (prune_empty(x) for x in v) if px not in ("", None)]
    return v


def sanitize_bson(doc: dict) -> dict:
    return prune_empty(convert_decimals(doc))


def safe_object_id(value: Any):
    if not value:
        return None
    try:
        return ObjectId(str(value))
    except Exception:
        return None
