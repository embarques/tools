from __future__ import annotations

from typing import Any, Dict

from pg2mongo.utils import decimal_to_float, to_utc

# Postgres account_chart_id → Mongo accounts[0] (legacy app IDs from Go importer)
_ACCOUNT_CHART_MONGO: dict[int, dict[str, Any]] = {
    1: {"id": 1, "name": "CASH ON HAND", "type": "Asset"},
    2: {"id": 3, "name": "ACCOUNTS RECEIVABLE", "type": "Asset"},
    6: {"id": 5, "name": "SALES", "type": "Revenue"},
    18: {"id": 4, "name": "SALES DISCOUNTS", "type": "Revenue"},
}


def _build_account(row: Dict[str, Any]) -> Dict[str, Any]:
    chart_id = int(row.get("account_chart_id") or 0)
    credit = decimal_to_float(row.get("credit") or 0)
    debit = decimal_to_float(row.get("debit") or 0)

    base = _ACCOUNT_CHART_MONGO.get(chart_id)
    if base:
        account = dict(base)
    else:
        account = {
            "id": chart_id,
            "name": row.get("account_chart_name") or row.get("account_chart_description") or "",
            "type": row.get("account_type") or "",
        }

    if credit > 0:
        account["credit"] = credit
    else:
        account["debit"] = debit

    return account


def build_journal_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a ``vwgeneral_journal`` row into a MongoDB journal document.

    ``invoice._id`` is set later when the parent invoice is written.
    """
    payment_type = row.get("payment_method_payment_type") or "CASH"
    payment_method_id = int(row.get("payment_method_id") or 0)

    doc: Dict[str, Any] = {
        "oldID": int(row["id"]),
        "description": row.get("trans_description") or "",
        "date": to_utc(row.get("trans_date")),
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
        "transactionID": int(row.get("transaction_id") or 0),
        "user": {"id": int(row.get("created_by_id") or 0)},
        "refNumber": row.get("ref_number") or "",
        "paymentMethod": {
            "id": payment_method_id,
            "name": payment_type,
        },
        "incomeStatement": {
            "id": int(row.get("income_statement_id") or 0),
            "rate": decimal_to_float(row.get("rate")),
            "branch": {"id": int(row.get("branch_id") or 0)},
        },
        "customer": {"oldID": int(row.get("customer_id") or 0)},
        "transactionBalance": decimal_to_float(row.get("open_balance_temp")),
        "transactionType": row.get("transaction_type_description") or "",
        "accounts": [_build_account(row)],
    }

    return doc
