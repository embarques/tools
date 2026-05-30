from datetime import datetime, timezone

from pg2mongo.builders.journal_build import build_journal_doc


def test_build_journal_doc_maps_account_chart_and_amounts():
    ts = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    row = {
        "id": 99,
        "time_created": ts,
        "time_modified": ts,
        "trans_date": ts,
        "trans_description": "Payment",
        "debit": 0,
        "credit": 150.5,
        "ref_number": "REF1",
        "account_chart_id": 1,
        "transaction_id": 7,
        "created_by_id": 3,
        "payment_method_id": 2,
        "payment_method_payment_type": "CASH",
        "branch_id": 1,
        "customer_id": 42,
        "income_statement_id": 10,
        "rate": 1.0,
        "open_balance_temp": 0,
        "transaction_type_description": "PAYMENT",
    }

    doc = build_journal_doc(row)

    assert doc["oldID"] == 99
    assert doc["description"] == "Payment"
    assert doc["accounts"][0]["_id"] == 1
    assert doc["accounts"][0]["name"] == "CASH ON HAND"
    assert doc["accounts"][0]["credit"] == 150.5
    assert doc["incomeStatement"]["_id"] == 10
    assert doc["customer"]["oldID"] == 42
