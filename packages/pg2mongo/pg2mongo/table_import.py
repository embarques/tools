from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

import click
from pymongo import UpdateOne
from pymongo.database import Database

from pg2mongo import collections as cols
from pg2mongo.builders.city_build import build_city_doc
from pg2mongo.builders.invoice_description_build import build_invoice_description_doc
from pg2mongo.sequences import ensure_counter
from pg2mongo.utils import pg_row_to_dict


BuildFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class TableImportSpec:
    """Postgres table → Mongo collection import definition."""

    pg_table: str
    mongo_collection: str
    sql: str
    build_doc: BuildFn
    counter_name: str | None = None


def postgres_table_to_collection(pg_table: str) -> str:
    """
    Derive the Mongo collection name from a Postgres table name.

    Known tables use explicit mappings; others default to snake_case with a
    trailing ``s`` when the table name is not already plural.
    """
    return TABLE_IMPORTS[pg_table].mongo_collection if pg_table in TABLE_IMPORTS else _default_collection_name(pg_table)


def _default_collection_name(pg_table: str) -> str:
    name = pg_table.strip().lower()
    if name.endswith("s"):
        return name
    return f"{name}s"


TABLE_IMPORTS: dict[str, TableImportSpec] = {
    "city": TableImportSpec(
        pg_table="city",
        mongo_collection=cols.CITIES,
        sql="""
            SELECT id, name, state_name, country_code, country, active, time_modified
            FROM city
            ORDER BY id
        """,
        build_doc=build_city_doc,
        counter_name="city_id",
    ),
    "invoice_description": TableImportSpec(
        pg_table="invoice_description",
        mongo_collection=cols.INVOICE_DESCRIPTIONS,
        sql="""
            SELECT id, description, price, time_created
            FROM invoice_description
            ORDER BY id
        """,
        build_doc=build_invoice_description_doc,
        counter_name="invoice_description_id",
    ),
}


def parse_table_list(tables: str) -> list[str]:
    """Parse a comma-separated list of Postgres table names."""
    return [part.strip().lower() for part in tables.split(",") if part.strip()]


def resolve_table_specs(table_names: Iterable[str]) -> list[TableImportSpec]:
    unknown = [name for name in table_names if name not in TABLE_IMPORTS]
    if unknown:
        known = ", ".join(sorted(TABLE_IMPORTS))
        raise click.ClickException(
            f"Unknown table(s): {', '.join(unknown)}. Supported: {known}"
        )
    return [TABLE_IMPORTS[name] for name in table_names]


def _max_numeric_id(db: Database, collection: str) -> int:
    doc = db[collection].find_one(
        {"_id": {"$type": "number"}},
        sort=[("_id", -1)],
        projection={"_id": 1},
    )
    if doc and isinstance(doc.get("_id"), int):
        return int(doc["_id"])
    return 0


def sync_counter_from_collection(
    db: Database,
    collection: str,
    counter_name: str,
) -> int:
    """Set counter *counter_name* to at least the max numeric ``_id`` in *collection*."""
    max_id = _max_numeric_id(db, collection)
    ensure_counter(db, counter_name, initial=max_id)
    if max_id > 0:
        db[cols.COUNTERS].update_one(
            {"_id": counter_name},
            {"$max": {"sequenceValue": max_id}},
        )
    return max_id


def fetch_rows(pg_conn, sql: str) -> list[dict[str, Any]]:
    with pg_conn.cursor() as cur:
        cur.execute(sql)
        col_names = [desc[0] for desc in cur.description]
        return [pg_row_to_dict(row, col_names) for row in cur.fetchall()]


def import_table(
    pg_conn,
    db: Database,
    spec: TableImportSpec,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    verbose: bool = False,
) -> dict[str, int]:
    """Import one Postgres table into its Mongo collection."""
    rows = fetch_rows(pg_conn, spec.sql)
    if limit is not None:
        rows = rows[:limit]

    if verbose:
        click.secho(
            f"[{spec.pg_table}] Loaded {len(rows)} row(s) from Postgres",
            fg="cyan",
        )

    if not rows:
        click.secho(f"[{spec.pg_table}] No rows to import.", fg="yellow")
        return {"matched": 0, "modified": 0, "upserted": 0}

    ops: list[UpdateOne] = []
    for row in rows:
        doc = spec.build_doc(row)
        if verbose:
            click.secho(
                f"[{spec.pg_table}] _id={doc.get('_id')} name={doc.get('name', '')!r}",
                fg="blue",
            )
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": doc},
                upsert=True,
            )
        )

    if dry_run:
        click.secho(
            f"[dry-run] Would upsert {len(ops)} document(s) into "
            f"{cols.qualified(db.name, spec.mongo_collection)}",
            fg="yellow",
        )
        return {"matched": 0, "modified": 0, "upserted": len(ops)}

    coll = db[spec.mongo_collection]
    result = coll.bulk_write(ops, ordered=False)

    if spec.counter_name:
        max_id = sync_counter_from_collection(db, spec.mongo_collection, spec.counter_name)
        if verbose and max_id:
            click.secho(
                f"[{spec.pg_table}] Counter {spec.counter_name} synced to >= {max_id}",
                fg="cyan",
            )

    return {
        "matched": result.matched_count,
        "modified": result.modified_count,
        "upserted": len(result.upserted_ids),
    }
