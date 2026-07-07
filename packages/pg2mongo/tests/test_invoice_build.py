from pg2mongo.builders.invoice_build import build_invoice_doc


def test_build_invoice_doc_uses_api_shape():
    doc = build_invoice_doc(
        {
            "id": 1001,
            "number": "INV-1001",
            "branch_id": 1,
            "branch_code": "NYC",
            "container_id": 2,
            "container_designation": "Container A",
            "driver_id": 5,
            "driver.name": "Tasador",
            "user_id": 9,
            "user.name": "tasador1",
            "cost": 120,
            "payment": 20,
            "balance": 100,
            "discount": 0,
            "recharge": 0,
            "paid_region": "",
            "paid_status": "PARTIAL",
            "registration": "completed",
            "sender.id": 11,
            "sender.name": "Sender Co",
            "sender.cus_type": 0,
            "sender.phone1": "305-555-1000",
            "sender.address.address1": "123 Main",
            "sender.address.city": "Miami",
            "sender.address.state": "FL",
            "sender.address.zipcode": "33101",
            "receiver.id": 12,
            "receiver.name": "Receiver Co",
            "receiver.cus_type": 1,
            "receiver.phone1": "(305) 555-2000",
        }
    )

    assert doc["branch"] == {"id": 1, "code": "NYC"}
    assert doc["container"] == {"id": 2, "name": "Container A"}
    assert doc["user"] == {"id": 9, "userName": "tasador1", "fullName": "tasador1"}
    assert doc["employee"] == {
        "id": 5,
        "name": "Tasador",
        "fullName": "Tasador",
    }
    assert doc["sender"]["customerType"] == 1
    assert doc["sender"]["phones"] == [
        {"type": "business", "number": "+13055551000", "isPrimary": True}
    ]
    assert doc["sender"]["addresses"][0]["address1"] == "123 Main"
    assert "address" not in doc["sender"]
    assert doc["receivers"][0]["customerType"] == 2
    assert doc["receivers"][0]["phones"] == [
        {"type": "mobile", "number": "+13055552000", "isPrimary": True}
    ]
    assert "receiver" not in doc
    assert doc["invoiceDetails"] == []


def test_build_invoice_doc_normalizes_legacy_receiver_object():
    doc = build_invoice_doc(
        {
            "number": "INV-1002",
            "receiver": {
                "id": "abc123",
                "name": "Maria",
                "customerType": 1,
            },
        }
    )

    assert doc["receivers"] == [
        {
            "_id": "abc123",
            "name": "Maria",
            "customerType": 2,
        }
    ]
    assert "receiver" not in doc


def test_build_invoice_doc_keeps_receivers_array():
    doc = build_invoice_doc(
        {
            "number": "INV-1003",
            "receivers": [
                {"_id": "r1", "name": "Maria", "customerType": 2},
                {"id": "r2", "name": "Jose"},
            ],
        }
    )

    assert doc["receivers"] == [
        {"_id": "r1", "name": "Maria", "customerType": 2},
        {"_id": "r2", "name": "Jose", "customerType": 2},
    ]
