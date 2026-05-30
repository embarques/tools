from __future__ import annotations

from typing import Any, Dict, Optional

from pg2mongo.utils import decimal_to_float, to_utc


def _optional_ref(
    entity_id: Any,
    name: str | None = None,
) -> Optional[Dict[str, Any]]:
    ref_id = int(entity_id or 0)
    if ref_id <= 0:
        return None
    ref: Dict[str, Any] = {"_id": ref_id}
    if name:
        ref["name"] = name
    return ref


def build_income_statement_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres ``income_statement`` row (with optional joins) to MongoDB.

    Mongo ``_id`` is the Postgres ``income_statement.id`` (numeric), matching the
    legacy Go importer and ``journal.incomeStatement._id`` references.
    """
    branch_id = int(row.get("branch_id") or 0)
    branch: Dict[str, Any] = {"_id": branch_id}
    if row.get("branch_code"):
        branch["code"] = row["branch_code"]
    if row.get("branch_name"):
        branch["name"] = row["branch_name"]

    doc: Dict[str, Any] = {
        "_id": int(row["id"]),
        "date": to_utc(row.get("stmt_date")),
        "branch": branch,
        "rate": decimal_to_float(row.get("rate")),
        "currency": row.get("currency") or "",
        "status": row.get("state") or "",
        "summaryTotal": {
            "invoices": decimal_to_float(row.get("invoice_total")),
            "receipts": decimal_to_float(row.get("receipt_total")),
            "otherIncomes": decimal_to_float(row.get("other_incomes")),
            "expenses": decimal_to_float(row.get("expenses")),
            "accountReceivables": decimal_to_float(row.get("account_receivable")),
            "discounts": decimal_to_float(row.get("discounts")),
            # Legacy BSON key spelling from Go models
            "accountsTranfer": decimal_to_float(row.get("accounts_transfer")),
            "loans": decimal_to_float(row.get("loans")),
        },
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
    }

    supervisor = _optional_ref(row.get("supervisor_id"), row.get("supervisor_name"))
    if supervisor:
        doc["supervisor"] = supervisor

    container = _optional_ref(
        row.get("container_id"),
        row.get("container_designation"),
    )
    if container:
        doc["container"] = container

    delivery = _optional_ref(row.get("delivery_id"), row.get("delivery_number"))
    if delivery:
        doc["delivery"] = delivery

    return doc
