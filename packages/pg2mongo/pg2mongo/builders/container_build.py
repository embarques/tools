from __future__ import annotations

from typing import Any, Dict

from pg2mongo.utils import to_utc, decimal_to_float


def build_container_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres container row into the MongoDB container document.

    Expected row keys (from SQL):
      id, designation, booking_number, container_number, broker,
      trans_company, cost, departure_date, arrival_date,
      time_created, time_modified
    """
    return {
        # Use Postgres ID as Mongo _id so it matches invoice.container._id references
        "_id": row["id"],

        # Basic identity / description
        "name": row.get("designation") or "",

        # Shipping-related fields
        "booking": row.get("booking_number") or "",
        "number": row.get("container_number") or "",
        "broker": row.get("broker") or "",
        "company": row.get("trans_company") or "",

        # Money (cost may come as Decimal)
        "cost": decimal_to_float(row.get("cost")) if row.get("cost") is not None else 0.0,

        # Dates
        "departureDate": to_utc(row.get("departure_date")),
        "arrivalDate": to_utc(row.get("arrival_date")),
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
    }
