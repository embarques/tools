from pg2mongo.utils import pg_row_to_dict


def test_pg_row_to_dict_with_dict_row():
    row = {"id": 166690, "quantity": 2, "description": "Box"}
    assert pg_row_to_dict(row) == row


def test_pg_row_to_dict_with_tuple_row():
    cols = ["id", "quantity", "description"]
    row = (166690, 2, "Box")
    assert pg_row_to_dict(row, cols) == {
        "id": 166690,
        "quantity": 2,
        "description": "Box",
    }


def test_pg_row_to_dict_avoids_column_name_values_bug():
    """zip(col_names, dict_row) incorrectly maps values to column name strings."""
    row = {"id": 166690, "quantity": 2}
    broken = dict(zip(["id", "quantity"], row))
    assert broken == {"id": "id", "quantity": "quantity"}

    fixed = pg_row_to_dict(row, ["id", "quantity"])
    assert fixed["id"] == 166690
    assert fixed["quantity"] == 2
