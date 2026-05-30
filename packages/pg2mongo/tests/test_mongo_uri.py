from __future__ import annotations

import pytest

from pg2mongo.mongo_uri import (
    build_mongo_uri,
    redact_mongo_uri,
    sanitize_mongo_uri,
    uri_has_credentials,
)


def test_uri_has_credentials_embedded():
    uri = "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true"
    assert uri_has_credentials(uri) is True


def test_uri_has_credentials_no_auth():
    uri = "mongodb://host1:27017,host2:27017/?replicaSet=rs0"
    assert uri_has_credentials(uri) is False


def test_build_mongo_uri_injects_replica_set():
    base = "mongodb://host1:27017,host2:27017/?replicaSet=rs0&authSource=admin"
    built = build_mongo_uri(base, "admin", "secret", sanitize=False)
    assert built == "mongodb://admin:secret@host1:27017,host2:27017/?replicaSet=rs0&authSource=admin"


def test_build_mongo_uri_injects_atlas_srv():
    base = "mongodb+srv://cluster.mongodb.net/?retryWrites=true&authSource=admin"
    built = build_mongo_uri(base, "admin", "secret", sanitize=False)
    assert built == "mongodb+srv://admin:secret@cluster.mongodb.net/?retryWrites=true&authSource=admin"


def test_build_mongo_uri_keeps_embedded_credentials():
    uri = "mongodb+srv://admin:secret@cluster.mongodb.net/?retryWrites=true"
    assert build_mongo_uri(uri, "other", "wrong", sanitize=False) == uri


def test_build_mongo_uri_no_injection_without_username():
    base = "mongodb://host1:27017/?replicaSet=rs0"
    assert build_mongo_uri(base, "", "", sanitize=False) == base


def test_sanitize_mongo_uri_strips_studio3t_params():
    uri = (
        "mongodb+srv://user:pass@cluster.mongodb.net/"
        "?retryWrites=true&3t.uriVersion=3&3t.connection.name=test"
    )
    cleaned = sanitize_mongo_uri(uri)
    assert "3t." not in cleaned
    assert "retryWrites=true" in cleaned


def test_redact_mongo_uri():
    uri = "mongodb+srv://admin:secret@cluster.mongodb.net/?retryWrites=true"
    assert redact_mongo_uri(uri) == "mongodb+srv://***:***@cluster.mongodb.net/?retryWrites=true"
