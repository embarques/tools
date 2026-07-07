from datetime import datetime, timezone

from pg2mongo.builders.pickup_build import format_pickup_verbose


def test_format_pickup_verbose_line():
    doc = {
        "_id": 42,
        "date": datetime(2026, 3, 15, tzinfo=timezone.utc),
        "sender": {
            "name": "Maria Lopez",
            "phones": [
                {"type": "mobile", "number": "+18095551234", "isPrimary": True}
            ],
            "addresses": [{"city": "Santiago", "isPrimary": True}],
        },
    }
    line = format_pickup_verbose(doc, action="new")
    assert "new id=42" in line
    assert "Maria Lopez" in line
    assert "+18095551234" in line
    assert "Santiago" in line
    assert "2026-03-15" in line
