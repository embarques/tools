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
            "registration": "completed",
            "sender.id": 11,
            "sender.name": "Sender Co",
            "sender.cus_type": 0,
            "sender.phone1": "305-555-1000",
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
    assert doc["user"] == {"_id": 9, "userName": "tasador1", "fullName": "tasador1"}
    assert doc["employee"] == {
        "_id": 5,
        "name": "Tasador",
        "fullName": "Tasador",
    }
    assert doc["sender"]["oldID"] == 11
    assert doc["sender"]["customerType"] == 1
    assert doc["sender"]["phone1"] == "305-555-1000"
    assert doc["sender"]["address"] == {
        "address1": "",
        "address2": "",
        "apartment": "",
        "city": "Miami",
        "state": "FL",
        "zipcode": "33101",
        "country": "",
    }
    assert doc["receiver"]["oldID"] == 12
    assert doc["receiver"]["customerType"] == 2
    assert doc["receiver"]["phone1"] == "(305) 555-2000"
    assert doc["invoiceDetails"] == []
    assert doc["registration"] == "completed"
    assert doc["isVoid"] is False
    assert "invoice_details" not in doc
    assert "driver" not in doc


def test_build_invoice_doc_keeps_raw_phone_strings():
    doc = build_invoice_doc(
        {
            "id": 1002,
            "sender.id": 11,
            "sender.cus_type": 0,
            "sender.phone1": "1 305 555 1000",
        }
    )

    assert doc["sender"]["phone1"] == "1 305 555 1000"
