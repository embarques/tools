from __future__ import annotations

from typing import Any, Dict

from pg2mongo.utils import to_float, to_utc


def build_invoice_description_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Postgres ``invoice_description`` row into ``invoice_descriptions``."""
    doc: Dict[str, Any] = {
        "_id": int(row["id"]),
        "name": row.get("description") or row.get("name") or "",
        "price": to_float(row.get("price")),
    }

    created_at = to_utc(row.get("time_created"))
    if created_at is not None:
        doc["createdAt"] = created_at
        doc["updatedAt"] = created_at

    return doc
