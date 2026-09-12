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
            "sender.address.apt": "2B",
            "sender.address.city": "Miami",
            "sender.address.state": "FL",
            "sender.address.zipcode": "33101",
            "receiver.id": 12,
            "receiver.name": "Receiver Co",
            "receiver.cus_type": 1,
            "receiver.phone1": "(305) 555-2000",
        }
    )

    assert doc["branch"] == {"_id": 1, "code": "NYC"}
    assert doc["container"] == {"_id": 2, "name": "Container A"}
    assert doc["createdBy"] == {"_id": 9, "name": "tasador1"}
    assert doc["employee"] == {"_id": 5, "name": "Tasador"}
    assert "user" not in doc
    assert "userName" not in doc["employee"]
    assert "fullName" not in doc["employee"]
    assert doc["registration"] == "COMPLETED"
    assert doc["sender"]["customerType"] == 1
    assert doc["sender"]["phones"] == [
        {"type": "business", "number": "+13055551000", "isPrimary": True}
    ]
    assert doc["sender"]["address"]["address1"] == "123 Main"
    assert doc["sender"]["address"]["city"] == "Miami"
    assert doc["sender"]["address"]["zipcode"] == "33101"
    assert doc["sender"]["address"]["apartment"] == "2B"
    assert "isPrimary" not in doc["sender"]["address"]
    assert "active" not in doc["sender"]
    assert "branch" not in doc["sender"]
    assert doc["receiver"]["customerType"] == 2
    assert doc["receiver"]["phones"] == [
        {"type": "mobile", "number": "+13055552000", "isPrimary": True}
    ]
    assert "receivers" not in doc
    assert doc["invoiceDetails"] == []
