import pytest

from pg2mongo import collections as cols
from pg2mongo.table_import import (
    parse_table_list,
    postgres_table_to_collection,
    resolve_table_specs,
)


def test_parse_table_list():
    assert parse_table_list("city, invoice_description") == [
        "city",
        "invoice_description",
    ]


def test_postgres_table_to_collection():
    assert postgres_table_to_collection("city") == cols.CITIES
    assert postgres_table_to_collection("invoice_description") == cols.INVOICE_DESCRIPTIONS


def test_resolve_table_specs():
    specs = resolve_table_specs(["city", "invoice_description"])
    assert [s.pg_table for s in specs] == ["city", "invoice_description"]
    assert specs[0].mongo_collection == "cities"
    assert specs[1].mongo_collection == "invoice_descriptions"


def test_resolve_table_specs_unknown():
    with pytest.raises(Exception) as exc:
        resolve_table_specs(["missing_table"])
    assert "Unknown table" in str(exc.value)


def test_tables_cmd_help():
    from click.testing import CliRunner
    from pg2mongo.transfer.tables import tables_cmd

    runner = CliRunner()
    result = runner.invoke(tables_cmd, ["--help"])
    assert result.exit_code == 0
    assert "--tables" in result.output
