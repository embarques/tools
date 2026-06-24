from __future__ import annotations

from typing import Any, Dict

from pg2mongo.utils import to_utc


def build_city_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Postgres ``city`` row into the tenant ``cities`` document."""
    return {
        "_id": int(row["id"]),
        "name": row.get("name") or "",
        "stateName": row.get("state_name") or "",
        "country": row.get("country_code") or row.get("country") or "",
        "active": bool(row.get("active", True)),
        "updatedAt": to_utc(row.get("time_modified")),
    }
