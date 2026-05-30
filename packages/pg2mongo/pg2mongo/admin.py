from __future__ import annotations
from typing import List, Tuple
from pymongo import ASCENDING, IndexModel
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import CollectionInvalid
from pymongo import UpdateOne
from rich.console import Console

from pg2mongo import collections as cols

console = Console()


def _create_collection_if_missing(db: Database, name: str) -> Collection:
    try:
        db.create_collection(name)
        console.print(f"[green]Created collection[/green]: {name}")
    except CollectionInvalid:
        pass
    return db[name]


def _drop_all_indexes(collection: Collection) -> None:
    collection.drop_indexes()


def create_unique_index(db: Database, collection_name: str, keys: List[Tuple[str, int]], *, name: str | None = None, drop_existing: bool = False) -> None:
    coll = _create_collection_if_missing(db, collection_name)
    if drop_existing:
        _drop_all_indexes(coll)
    if not name:
        name = "uniq_" + "_".join([f"{k}_{'asc' if v == 1 else 'desc'}" for k, v in keys])
    model = IndexModel(keys, name=name, unique=True)
    created = coll.create_indexes([model])
    console.print(f"[cyan]Index ensured[/cyan] on [bold]{collection_name}[/bold]: {created}")


def ensure_business_indexes(db: Database, *, drop_existing: bool = False) -> None:
    create_unique_index(db, cols.BRANCHES, [("name", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.CUSTOMERS, [("name", ASCENDING), ("phone1", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.INVOICES, [("number", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.USERS, [("userName", ASCENDING), ("roles", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.CONTAINERS, [("name", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.ACCOUNTS, [("name", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.INCOME_STATEMENTS, [("date", ASCENDING), ("branch.code", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.ROLES, [("name", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.PERMISSIONS, [("name", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.CITIES, [("name", ASCENDING)], drop_existing=drop_existing)
    create_unique_index(db, cols.PICKUPS, [("date", ASCENDING), ("sender.name", ASCENDING), ("sender.address.address1", ASCENDING)], drop_existing=drop_existing)

    for cname in (cols.ACTIVITY_LOGS, cols.INVOICE_DETAILS, cols.JOURNALS, cols.COUNTERS):
        _create_collection_if_missing(db, cname)


def seed_counters(db: Database) -> None:
    counters = [
        ("user_id", 0),
        ("container_id", 0),
        ("chart_account_id", 0),
        ("income_statement_id", 0),
        ("app_menu_id", 0),
        ("permission_id", 0),
        ("role_id", 0),
        ("invoice_description_id", 0),
        ("city_id", 0),
        ("pickup_id", 0),
        ("employee_id", 0),
        ("delivery_id", 0),
    ]
    coll = _create_collection_if_missing(db, cols.COUNTERS)
    ops = [UpdateOne({"_id": cid}, {"$setOnInsert": {"_id": cid, "sequenceValue": seq}}, upsert=True) for cid, seq in counters]
    if ops:
        res = coll.bulk_write(ops, ordered=False)
        console.print(f"[green]Counters ensured[/green] (upserted: {getattr(res, 'upserted_count', 0)})")
