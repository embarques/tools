from __future__ import annotations

from typing import Any, Dict

from pg2mongo.utils import to_utc


def build_delivery_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres delivery row from vwdelivery_api into the MongoDB delivery document.

    Expected row keys from SQL:
      id,
      time_created,
      time_modified,
      delivery_number,
      container_id,
      container_designation,
      delivery_date,
      employee_id,
      employee_name,
      helper1_id,
      helper1_name,
      helper2_id,
      helper2_name
    """

    # Container subdocument
    container: Dict[str, Any] | None = None
    if row.get("container_id"):
        container = {
            "_id": row.get("container_id"),
            "name": row.get("container_designation") or "",
        }

    # Employee subdocs
    employee: Dict[str, Any] | None = None
    if row.get("employee_id"):
        employee = {
            "_id": row.get("employee_id"),
            "name": row.get("employee_name") or "",
        }

    helper1: Dict[str, Any] | None = None
    if row.get("helper1_id"):
        helper1 = {
            "_id": row.get("helper1_id"),
            "name": row.get("helper1_name") or "",
        }

    helper2: Dict[str, Any] | None = None
    if row.get("helper2_id"):
        helper2 = {
            "_id": row.get("helper2_id"),
            "name": row.get("helper2_name") or "",
        }

    doc: Dict[str, Any] = {
        "_id": row["id"],
        "name": row.get("delivery_number") or "",
        "container": container,
        "employee": employee,
        "helper1": helper1,
        "helper2": helper2,
        "date": to_utc(row.get("delivery_date")),
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
    }

    return doc
