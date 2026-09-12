from datetime import datetime, timezone

from pg2mongo.builders.pickup_build import build_pickup_doc


def test_build_pickup_doc_uses_transaction_address_snapshots():
    ts = datetime(2026, 6, 10, 8, 0, tzinfo=timezone.utc)
    doc = build_pickup_doc(
        {
            "pickup_date": ts,
            "pickup_created": ts,
            "pickup_modified": ts,
            "completed": False,
            "purpose": "Pickup boxes",
            "sector_id": 1,
            "sector_name": "North",
            "branch.id": 1,
            "branch.code": "NYC",
            "employee.id": 5,
            "employee.name": "Jane Driver",
            "user.id": 9,
            "user.name": "dispatcher",
            "sender.id": 11,
            "sender.name": "Sender Name",
            "sender.cus_type": 0,
            "sender.phone1": "3055553000",
            "sender.address.address1": "2490 Davidson Ave",
            "sender.address.apt": "2B",
            "sender.address.city": "Bronx",
            "sender.address.state": "NY",
            "sender.address.zipcode": "10468",
            "receiver.id": 12,
            "receiver.name": "Receiver Name",
            "receiver.cus_type": 1,
            "receiver.phone1": "3055554000",
            "receiver.address.address1": "10 Oak Ave",
            "receiver.address.city": "Miami",
            "receiver.address.state": "FL",
            "receiver.address.zipcode": "33101",
        }
    )

    assert doc["branch"] == {"_id": 1, "code": "NYC"}
    assert "user" not in doc
    assert "employee" not in doc
    assert "sector" not in doc
    assert doc["completed"] is False

    sender = doc["sender"]
    assert sender["address"]["address1"] == "2490 Davidson Ave"
    assert sender["address"]["apartment"] == "2B"
    assert sender["address"]["city"] == "Bronx"
    assert "addresses" not in sender
    assert "isPrimary" not in sender["address"]
    assert "active" not in sender

    receivers = doc["receivers"]
    assert len(receivers) == 1
    assert receivers[0]["address"]["address1"] == "10 Oak Ave"
    assert receivers[0]["address"]["city"] == "Miami"
    assert "addresses" not in receivers[0]
    assert "receiver" not in doc
