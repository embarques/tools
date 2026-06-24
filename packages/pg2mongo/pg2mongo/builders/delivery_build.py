from __future__ import annotations

from typing import Any, Dict

from pg2mongo.builders.embedded import container_snapshot, employee_snapshot
from pg2mongo.utils import to_utc


def build_delivery_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Postgres delivery row from vwdelivery_api into the deliveries document."""
    container = None
    if row.get("container_id"):
        container = container_snapshot(
            row.get("container_id"),
            name=row.get("container_designation") or "",
            container_number=row.get("container_number") or "",
        )

    employee = None
    if row.get("employee_id"):
        employee = employee_snapshot(
            row.get("employee_id"),
            name=row.get("employee_name") or "",
        )

    helper1 = None
    if row.get("helper1_id"):
        helper1 = employee_snapshot(
            row.get("helper1_id"),
            name=row.get("helper1_name") or "",
        )

    helper2 = None
    if row.get("helper2_id"):
        helper2 = employee_snapshot(
            row.get("helper2_id"),
            name=row.get("helper2_name") or "",
        )

    delivery_dt = to_utc(row.get("delivery_date"))

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("delivery_number") or "",
        "container": container,
        "employee": employee,
        "helper1": helper1,
        "helper2": helper2,
        "date": delivery_dt,
        "createdAt": delivery_dt,
        "updatedAt": delivery_dt,
    }

    return doc
