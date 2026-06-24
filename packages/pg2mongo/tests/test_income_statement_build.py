from datetime import date, datetime, timezone

from pg2mongo.builders.income_statement_build import build_income_statement_doc


def test_build_income_statement_doc():
    stmt_date = date(2026, 1, 15)
    ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    row = {
        "id": 42,
        "stmt_date": stmt_date,
        "branch_id": 1,
        "branch_code": "TN",
        "branch_name": "Tenares",
        "supervisor_id": 5,
        "supervisor_name": "Supervisor",
        "rate": 1.0,
        "currency": "dollar",
        "state": "CLOSED",
        "time_created": ts,
        "time_modified": ts,
        "invoice_total": 100,
        "receipt_total": 80,
        "other_incomes": 0,
        "expenses": 10,
        "account_receivable": 20,
        "loans": 0,
        "discounts": 5,
        "accounts_transfer": 0,
    }

    doc = build_income_statement_doc(row)

    assert doc["_id"] == 42
    assert doc["branch"]["code"] == "TN"
    assert doc["branch"]["_id"] == 1
    assert doc["status"] == "CLOSED"
    assert doc["summaryTotal"]["invoices"] == 100.0
    assert doc["summaryTotal"]["accountsTransfer"] == 0.0
    assert doc["user"]["_id"] == 5
    assert doc["user"]["fullName"] == "Supervisor"
    assert "supervisor" not in doc
