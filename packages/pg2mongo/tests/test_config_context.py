from pathlib import Path

import click
import pytest

from pg2mongo.cli.context import get_config_path, get_verbose
from pg2mongo.config import _find_db_toml, load_settings, resolve_config_path


def test_get_config_path_from_parent_context():
    parent = click.Context(click.Command("root"))
    parent.obj = {"config_path": "/tmp/db.toml", "verbose": True}

    child = click.Context(click.Command("child"), parent=parent)
    child.obj = {}

    assert get_config_path(child) == "/tmp/db.toml"
    assert get_verbose(child) is True


def test_find_db_toml_in_project_root():
    path = _find_db_toml()
    assert path is not None
    assert path.name == "db.toml"
    assert "pg2mongo" in str(path)


def test_load_settings_without_explicit_path():
    settings = load_settings(None)
    assert settings.postgres.db
    assert settings.mongo.db


def test_resolve_config_path_explicit():
    db = _find_db_toml()
    assert resolve_config_path(str(db)) == db
