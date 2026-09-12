from pg2mongo.builders.user_build import build_user_doc, user_insert_op


def test_build_user_doc_uses_name_not_userName():
    doc = build_user_doc(
        {
            "id": 7,
            "username": "jdoe",
            "full_name": "John Doe",
            "email": "jdoe@example.com",
            "uid": "firebase-uid",
            "branch_id": 1,
            "branch_name": "Main",
            "is_active": True,
        }
    )
    assert doc["_id"] == 7
    assert doc["name"] == "John Doe"
    assert doc["uid"] == "firebase-uid"
    assert doc["email"] == "jdoe@example.com"
    assert doc["branch"] == {"_id": 1, "name": "Main"}
    assert "userName" not in doc
    assert "fullName" not in doc
    assert "password" not in doc
    assert "role" not in doc


def test_user_insert_op_does_not_update_existing_fields():
    doc = {
        "_id": 7,
        "uid": "firebase-uid",
        "name": "John Doe",
        "active": True,
    }

    op = user_insert_op(doc)

    assert op._filter == {"_id": 7}
    assert op._doc == {"$setOnInsert": {
        "uid": "firebase-uid",
        "name": "John Doe",
        "active": True,
    }}
    assert op._upsert is True
    assert "$set" not in op._doc
    assert "$unset" not in op._doc
