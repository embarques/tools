from pg2mongo.builders.customer_build import build_customer_doc
from pg2mongo.match_keys import customer_match_filter, invoice_match_filter, pickup_match_filter


def test_customer_match_filter_uses_id_number_when_present():
    doc = build_customer_doc(
        {
            "id": 99,
            "name": "Acme",
            "cus_type": 0,
            "id_number": "RNC-123",
            "phone1": "3055551000",
        }
    )
    assert customer_match_filter(doc) == {
        "name": "Acme",
        "customerType": 1,
        "IDNumber": "RNC-123",
    }
    assert "oldID" not in doc


def test_invoice_match_filter():
    assert invoice_match_filter({"number": "INV-1"}) == {"number": "INV-1"}


def test_pickup_match_filter():
    filt = pickup_match_filter(
        {
            "date": "2026-01-01",
            "sender": {
                "name": "Maria",
                "addresses": [{"isPrimary": True, "address1": "123 Main"}],
            },
        }
    )
    assert filt["sender.name"] == "Maria"
    assert filt["sender.addresses.address1"] == "123 Main"
