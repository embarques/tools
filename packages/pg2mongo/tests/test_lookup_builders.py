from pg2mongo.builders.city_build import build_city_doc
from pg2mongo.builders.invoice_description_build import build_invoice_description_doc


def test_build_city_doc():
    doc = build_city_doc(
        {
            "id": 3,
            "name": "Bronx",
            "state_name": "New York",
            "country_code": "US",
            "active": True,
        }
    )
    assert doc["_id"] == 3
    assert doc["name"] == "Bronx"
    assert doc["stateName"] == "New York"
    assert doc["country"] == "US"
    assert doc["active"] is True


def test_build_invoice_description_doc():
    doc = build_invoice_description_doc(
        {
            "id": 12,
            "description": "Handling fee",
            "price": "25.50",
        }
    )
    assert doc["_id"] == 12
    assert doc["name"] == "Handling fee"
    assert doc["price"] == 25.5
