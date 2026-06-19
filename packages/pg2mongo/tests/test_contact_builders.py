from pg2mongo.builders.customer_build import build_customer_doc
from pg2mongo.builders.employee_build import build_employee_doc


def test_build_customer_doc_uses_new_contact_shape():
    doc = build_customer_doc(
        {
            "id": 10,
            "name": "Acme Corp",
            "cus_type": 1,
            "phone1": "+12015550100",
            "phone2": "305-555-0101",
            "id_number": "123456789",
            "active": True,
            "branch_id": 1,
            "branch_code": "NYC",
            "branch_name": "New York",
            "address.address1": "123 Main St",
            "address.city": "Miami",
            "address.state": "FL",
            "address.zipcode": "33101",
            "address.country": "US",
        }
    )

    assert doc["oldID"] == 10
    assert doc["customerType"] == 2
    assert doc["phones"] == [
        {"type": "mobile", "number": "+12015550100", "isPrimary": True},
        {"type": "business", "number": "+13055550101"},
    ]
    assert doc["email"] == ""
    assert doc["IDNumber"] == "123456789"
    assert doc["notes"] == ""
    assert doc["branch"] == {"id": 1, "code": "NYC", "name": "New York"}
    assert doc["address"] == {
        "address1": "123 Main St",
        "city": "Miami",
        "state": "FL",
        "zipcode": "33101",
        "country": "US",
    }
    assert "phone1" not in doc
    assert "phone2" not in doc


def test_build_employee_doc_uses_new_contact_shape():
    doc = build_employee_doc(
        {
            "id": 7,
            "name": "Jane Driver",
            "title": "Driver",
            "department": "Delivery",
            "phone1": "+12125552000",
            "email": "jane@example.com",
            "branch_id": 1,
            "branch_code": "NYC",
            "address.city": "Bronx",
            "address.state": "NY",
            "address.zipcode": "10451",
        }
    )

    assert doc["_id"] == 7
    assert doc["phones"] == [
        {"type": "mobile", "number": "+12125552000", "isPrimary": True}
    ]
    assert doc["branch"] == {"id": 1, "code": "NYC"}
    assert doc["address"] == {
        "city": "Bronx",
        "state": "NY",
        "zipcode": "10451",
    }
    assert "phone1" not in doc
    assert "phone2" not in doc
