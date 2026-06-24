from __future__ import annotations

from typing import Any, Dict

from pg2mongo.builders.embedded import branch_dto, container_snapshot, employee_snapshot, user_snapshot
from pg2mongo.utils import decimal_to_float, to_utc


def _zero_summary_defaults() -> Dict[str, float]:
    return {
        "invoices": 0.0,
        "receipts": 0.0,
        "invoicePayments": 0.0,
        "receiptPayments": 0.0,
        "otherIncomes": 0.0,
        "cash": 0.0,
        "deposits": 0.0,
        "check": 0.0,
        "zelle": 0.0,
        "creditCards": 0.0,
        "expenses": 0.0,
        "accountReceivables": 0.0,
        "discounts": 0.0,
        "accountsTransfer": 0.0,
        "loans": 0.0,
        "totalIncome": 0.0,
        "totalGeneral": 0.0,
        "totalCash": 0.0,
        "netIncome": 0.0,
    }


def build_income_statement_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a Postgres ``income_statement`` row (with optional joins) to MongoDB.

    Mongo ``_id`` is the Postgres ``income_statement.id`` (uint32).
    """
    summary = _zero_summary_defaults()
    summary.update(
        {
            "invoices": decimal_to_float(row.get("invoice_total")),
            "receipts": decimal_to_float(row.get("receipt_total")),
            "otherIncomes": decimal_to_float(row.get("other_incomes")),
            "expenses": decimal_to_float(row.get("expenses")),
            "accountReceivables": decimal_to_float(row.get("account_receivable")),
            "discounts": decimal_to_float(row.get("discounts")),
            "accountsTransfer": decimal_to_float(row.get("accounts_transfer")),
            "loans": decimal_to_float(row.get("loans")),
        }
    )

    doc: Dict[str, Any] = {
        "_id": int(row["id"]),
        "date": to_utc(row.get("stmt_date")),
        "branch": branch_dto(
            row.get("branch_id"),
            name=row.get("branch_name") or "",
            code=row.get("branch_code") or "",
        ),
        "rate": decimal_to_float(row.get("rate")),
        "currency": row.get("currency") or "",
        "status": row.get("state") or "",
        "summaryTotal": summary,
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
    }

    user = user_snapshot(
        row.get("supervisor_id"),
        name=row.get("supervisor_name") or "",
        fullName=row.get("supervisor_name") or "",
    )
    if user.get("_id", 0) > 0:
        doc["user"] = user

    container = container_snapshot(
        row.get("container_id"),
        name=row.get("container_designation") or "",
    )
    if container.get("_id", 0) > 0:
        doc["container"] = container

    delivery_id = int(row.get("delivery_id") or 0)
    if delivery_id > 0:
        doc["delivery"] = {
            "_id": delivery_id,
            "name": row.get("delivery_number") or "",
        }

    return doc
