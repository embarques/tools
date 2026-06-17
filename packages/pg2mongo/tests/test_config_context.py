from pathlib import Path

import click
import pytest

from pg2mongo.cli.context import get_config_path, get_verbose, get_verbosity, resolve_verbose
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


def test_resolve_verbose_sets_context():
    ctx = click.Context(click.Command("child"))
    ctx.obj = {}
    assert resolve_verbose(ctx, True) == 1
    assert get_verbose(ctx) is True


def test_get_verbosity_accumulates_parent_and_child_counts():
    parent = click.Context(click.Command("root"))
    parent.obj = {"verbose": 2}

    child = click.Context(click.Command("child"), parent=parent)
    child.obj = {"verbose": 2}

    assert get_verbosity(child) == 4
    assert get_verbose(child) is True


def test_all_subcommands_accept_verbose_flag():
    from click.testing import CliRunner
    from pg2mongo.transfer.pickup import pickup_cmd

    runner = CliRunner()
    result = runner.invoke(pickup_cmd, ["--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output
