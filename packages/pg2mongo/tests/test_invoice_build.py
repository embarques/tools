from pg2mongo.builders.invoice_build import build_invoice_doc


def test_build_invoice_doc_uses_new_reference_shape():
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
            "sender.id": 11,
            "sender.name": "Sender Co",
            "sender.cus_type": 0,
            "sender.phone1": "+13055551000",
            "sender.address.city": "Miami",
            "sender.address.state": "FL",
            "sender.address.zipcode": "33101",
            "receiver.id": 12,
            "receiver.name": "Receiver Co",
            "receiver.cus_type": 1,
            "receiver.phone1": "+13055552000",
        }
    )

    assert doc["branch"] == {"id": 1, "code": "NYC"}
    assert doc["container"] == {"id": 2, "name": "Container A"}
    assert doc["employee"] == {
        "id": 5,
        "name": "Tasador",
        "userName": "tasador1",
        "fullName": "Tasador",
    }
    assert doc["sender"]["id"] == 11
    assert doc["sender"]["customerType"] == 1
    assert doc["sender"]["phones"] == [
        {"type": "business", "number": "+13055551000", "isPrimary": True}
    ]
    assert doc["sender"]["address"] == {
        "city": "Miami",
        "state": "FL",
        "zipcode": "33101",
    }
    assert doc["receiver"]["id"] == 12
    assert doc["receiver"]["customerType"] == 2
    assert doc["receiver"]["phones"] == [
        {"type": "mobile", "number": "+13055552000", "isPrimary": True}
    ]
    assert doc["invoiceDetails"] == []
    assert "invoice_details" not in doc
    assert "user" not in doc
    assert "driver" not in doc
