from __future__ import annotations

from datetime import datetime, timezone

import click
from pymongo.errors import PyMongoError

from pg2mongo import collections as cols
from pg2mongo.cli.context import get_config_path, get_verbose
from pg2mongo.transfer.common import (
    resolve_settings,
    connect_postgres_and_mongo,
    close_connections_safe,
)
from pg2mongo.utils import create_unique_index  # ← now from utils


@click.command("init-indexes")
@click.pass_context
def init_indexes_cmd(ctx: click.Context):
    """
    Initialize Mongo indexes and seed counters collection.
    """
    config_path = get_config_path(ctx)
    verbose = get_verbose(ctx)

    settings = resolve_settings(config_path, verbose)
    pg_conn = None
    mongo_client = None

    try:
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)
        db = mongo_client[settings.mongo.db]

        click.secho(f"Initializing counters on db={settings.mongo.db}", fg="cyan")

        # Seed counters
        counters_coll = db[cols.COUNTERS]

        counters = [
            {"_id": "user_id", "sequenceValue": 0},
            {"_id": "container_id", "sequenceValue": 0},
            {"_id": "chart_account_id", "sequenceValue": 0},
            {"_id": "income_statement_id", "sequenceValue": 0},
            {"_id": "app_menu_id", "sequenceValue": 0},
            {"_id": "permission_id", "sequenceValue": 0},
            {"_id": "role_id", "sequenceValue": 0},
            {"_id": "invoice_description_id", "sequenceValue": 0},
            {"_id": "city_id", "sequenceValue": 0},
            {"_id": "pickup_id", "sequenceValue": 0},
            {"_id": "employee_id", "sequenceValue": 0},
            {"_id": "delivery_id", "sequenceValue": 0},
        ]

        for c in counters:
            counters_coll.update_one(
                {"_id": c["_id"]},
                {"$setOnInsert": c},
                upsert=True,
            )

        # Touch collections that should exist without indexes
        for name in (cols.ACTIVITY_LOGS, cols.INVOICE_DETAILS, cols.JOURNALS):
            db[name].insert_one({"createdAt": datetime.now(timezone.utc)})
            db[name].delete_many({})  # leave them empty

        click.secho(f"Initializing indexes on db={settings.mongo.db}", fg="cyan")

        # Branches
        create_unique_index(db, cols.BRANCHES, {"name": 1})

        # Customers
        create_unique_index(db, cols.CUSTOMERS, {"name": 1, "phone1": 1})

        # Invoices
        create_unique_index(db, cols.INVOICES, {"number": 1})

        # Users
        create_unique_index(db, cols.USERS, {"userName": 1, "roles": 1})

        # Containers
        create_unique_index(db, cols.CONTAINERS, {"name": 1})

        # Accounts
        create_unique_index(db, cols.ACCOUNTS, {"name": 1})

        # Income statements
        create_unique_index(db, cols.INCOME_STATEMENTS, {"date": 1, "branch.code": 1})

        # Roles
        create_unique_index(db, cols.ROLES, {"name": 1})

        # Permissions
        create_unique_index(db, cols.PERMISSIONS, {"name": 1})

        # Cities
        create_unique_index(db, cols.CITIES, {"name": 1})

        # Pickups (unique by date + sender.name + sender.address.address1)
        create_unique_index(
            db,
            cols.PICKUPS,
            {"date": 1, "sender.name": 1, "sender.address.address1": 1},
        )

        click.secho("✅ Mongo index initialization complete.", fg="green")

    except PyMongoError as exc:
        click.secho("❌ Error while initializing indexes:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
        raise
    finally:
        close_connections_safe(pg_conn, mongo_client)
