from pg2mongo.builders.delivery_build import build_delivery_doc


def test_build_delivery_doc_uses_employees_array():
    doc = build_delivery_doc(
        {
            "id": 10,
            "delivery_number": "Route 1",
            "delivery_date": None,
            "container_id": 2,
            "container_designation": "Container A",
            "container_number": "MSCU123",
            "employee_id": 5,
            "employee_name": "Jane Driver",
            "helper1_id": 6,
            "helper1_name": "Helper One",
            "helper2_id": None,
            "helper2_name": "",
        }
    )

    assert doc["_id"] == 10
    assert doc["container"] == {
        "_id": 2,
        "name": "Container A",
        "containerNumber": "MSCU123",
    }
    assert doc["employees"] == [
        {"id": 5, "name": "Jane Driver"},
        {"id": 6, "name": "Helper One"},
    ]
    assert "employee" not in doc
    assert "helper1" not in doc
    assert "helper2" not in doc
