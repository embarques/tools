from datetime import date, datetime, timezone
from decimal import Decimal

from pg2mongo.builders.container_build import build_container_doc


def test_build_container_doc_maps_legacy_postgres_columns():
    """Postgres container row (id=1124) maps to API container fields."""
    departure = date(2023, 12, 5)
    created = datetime(2023, 12, 2, 17, 55, 19, 962180, tzinfo=timezone.utc)
    modified = datetime(2023, 12, 5, 20, 26, 52, 982507, tzinfo=timezone.utc)
    row = {
        "id": 1124,
        "designation": "99-23",
        "booking_number": "7864197-A",
        "seal_number": "UL-512374-5",
        "container_number": "SMLU-846026-8",
        "broker": "",
        "trans_company": "SUBWAY LOGISTICS",
        "cost": Decimal("0.00"),
        "departure_date": departure,
        "arrival_date": None,
        "time_created": created,
        "time_modified": modified,
    }

    doc = build_container_doc(row)

    assert doc["_id"] == 1124
    assert doc["name"] == "99-23"
    assert doc["booking"] == "7864197-A"
    assert doc["containerNumber"] == "SMLU-846026-8"
    assert doc["seal"] == "UL-512374-5"
    assert doc["sealNumber"] == "UL-512374-5"
    assert doc["company"] == "SUBWAY LOGISTICS"
    assert doc["cost"] == 0.0
    assert doc["departureDate"] == datetime(2023, 12, 5, tzinfo=timezone.utc)
    assert doc["arrivalDate"] is None
    assert doc["createdAt"] == created
    assert doc["updatedAt"] == modified
