from pg2mongo.customer_types import RECEIVER, SENDER, mongo_customer_type


def test_mongo_customer_type_maps_postgres_sender():
    assert mongo_customer_type(0) == SENDER


def test_mongo_customer_type_maps_postgres_receiver():
    assert mongo_customer_type(1) == RECEIVER


def test_mongo_customer_type_defaults_to_sender():
    assert mongo_customer_type(None) == SENDER
