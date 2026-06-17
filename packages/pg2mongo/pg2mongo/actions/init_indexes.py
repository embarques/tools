from __future__ import annotations

from datetime import datetime, timezone

import click
from pymongo.errors import PyMongoError

from pg2mongo import collections as cols
from pg2mongo.cli.context import get_config_path, resolve_verbose, verbose_option
from pg2mongo.transfer.common import (
    resolve_settings,
    connect_postgres_and_mongo,
    close_connections_safe,
)
from pg2mongo.utils import create_unique_index
from pg2mongo.sequences import ensure_counters


@click.command("init-indexes")
@verbose_option
@click.pass_context
def init_indexes_cmd(ctx: click.Context, verbose: int):
    """
    Initialize Mongo indexes and seed counters collection.
    """
    verbose = resolve_verbose(ctx, verbose)
    config_path = get_config_path(ctx)

    settings = resolve_settings(config_path, verbose)
    pg_conn = None
    mongo_client = None

    try:
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)
        db = mongo_client[settings.mongo.db]

        click.secho(f"Initializing counters on db={settings.mongo.db}", fg="cyan")

        created = ensure_counters(db)
        if verbose and created:
            click.secho(f"[counters] Created {created} new counter(s)", fg="cyan")

        # Touch collections that should exist without indexes
        for name in (cols.ACTIVITY_LOGS, cols.INVOICE_DETAILS, cols.JOURNALS):
            db[name].insert_one({"createdAt": datetime.now(timezone.utc)})
            db[name].delete_many({})  # leave them empty

        click.secho(f"Initializing indexes on db={settings.mongo.db}", fg="cyan")

        # Branches
        create_unique_index(db, cols.BRANCHES, {"name": 1})

        # Customers
        create_unique_index(db, cols.CUSTOMERS, {"name": 1, "phones.number": 1})

        # Invoices
        create_unique_index(db, cols.INVOICES, {"number": 1})

        # Journals (natural key from Postgres general_journal.id)
        create_unique_index(db, cols.JOURNALS, {"oldID": 1})

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
