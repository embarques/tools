from datetime import datetime, timezone

from pg2mongo.builders.pickup_build import format_pickup_verbose


def test_format_pickup_verbose_line():
    doc = {
        "_id": 42,
        "oldID": 323128,
        "date": datetime(2026, 3, 15, tzinfo=timezone.utc),
        "sender": {
            "name": "Maria Lopez",
            "phone1": "809-555-1234",
            "address": {"city": "Santiago"},
        },
    }
    line = format_pickup_verbose(doc, action="new")
    assert "new id=42" in line
    assert "Maria Lopez" in line
    assert "809-555-1234" in line
    assert "Santiago" in line
    assert "2026-03-15" in line
