from pg2mongo.builders.user_build import user_insert_op


def test_user_insert_op_does_not_update_existing_fields():
    doc = {
        "_id": 7,
        "uid": "firebase-uid",
        "userName": "jdoe",
        "fullName": "John Doe",
        "active": True,
    }

    op = user_insert_op(doc)

    assert op._filter == {"_id": 7}
    assert op._doc == {"$setOnInsert": {
        "uid": "firebase-uid",
        "userName": "jdoe",
        "fullName": "John Doe",
        "active": True,
    }}
    assert op._upsert is True
    assert "$set" not in op._doc
    assert "$unset" not in op._doc
