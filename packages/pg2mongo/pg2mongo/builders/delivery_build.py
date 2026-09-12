from __future__ import annotations

from typing import Any, Dict

from pg2mongo.builders.embedded import container_snapshot, employee_dto
from pg2mongo.utils import to_utc


def build_delivery_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres delivery row from vwdelivery_api into the deliveries document.

    Matches ``internal/delivery.Delivery``:
      employees[] uses employee.EmployeeDTO bson ``id`` (not ``_id``).
    """
    container = None
    if row.get("container_id"):
        container = container_snapshot(
            row.get("container_id"),
            name=row.get("container_designation") or "",
            container_number=row.get("container_number") or "",
        )

    employees: list[dict[str, Any]] = []
    for id_key, name_key in (
        ("employee_id", "employee_name"),
        ("helper1_id", "helper1_name"),
        ("helper2_id", "helper2_name"),
    ):
        emp_id = row.get(id_key)
        if not emp_id:
            continue
        employees.append(
            employee_dto(emp_id, name=row.get(name_key) or "")
        )

    delivery_dt = to_utc(row.get("delivery_date"))

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("delivery_number") or "",
        "container": container,
        "employees": employees,
        "date": delivery_dt,
        "createdAt": delivery_dt,
        "updatedAt": delivery_dt,
    }

    return doc
