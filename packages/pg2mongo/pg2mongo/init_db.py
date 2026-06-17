from __future__ import annotations

import sys
import time
from urllib.parse import urlparse

import click
from pymongo.errors import (
    ConfigurationError,
    InvalidURI,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from pg2mongo.admin import ensure_business_indexes, seed_counters
from pg2mongo.cli.context import get_config_path, resolve_verbose, verbose_option
from pg2mongo.clients import connect_mongo
from pg2mongo.mongo_uri import redact_mongo_uri
from pg2mongo.transfer.common import resolve_settings


@click.command("init-db")
@click.option("--drop-existing", is_flag=True, help="Drop and recreate indexes.")
@click.option("--dry-run", is_flag=True, help="Preview without making changes.")
@verbose_option
@click.pass_context
def init_db_cmd(
    ctx: click.Context,
    drop_existing: bool,
    dry_run: bool,
    verbose: int,
) -> None:
    """Initialize MongoDB: ensure indexes and seed counters (idempotent)."""
    verbose = resolve_verbose(ctx, verbose)
    config_path = get_config_path(ctx)
    settings = resolve_settings(config_path, verbose)

    mongo_client = None
    try:
        t0 = time.perf_counter()
        uri = settings.mongo.build_uri()

        try:
            mongo_client = connect_mongo(settings, verbose=verbose)
        except InvalidURI as exc:
            raise click.ClickException(
                f"MongoDB connection failed: Invalid URI.\n"
                f"  URI: {redact_mongo_uri(uri)}\n"
                f"  Details: {exc}"
            ) from exc
        except OperationFailure as exc:
            parsed = urlparse(uri)
            query = (
                dict(kv.split("=", 1) for kv in parsed.query.split("&") if "=" in kv)
                if parsed.query
                else {}
            )
            raise click.ClickException(
                f"MongoDB authentication failed.\n"
                f"  URI: {redact_mongo_uri(uri)}\n"
                f"  Username: {(parsed.username or '').strip() or '<none>'}\n"
                f"  authSource: {query.get('authSource', '<default>')}\n"
                f"  authMechanism: {query.get('authMechanism', '<default>')}\n"
                f"  Error: {exc}\n"
            ) from exc
        except ServerSelectionTimeoutError as exc:
            raise click.ClickException(
                f"MongoDB server selection timed out.\n"
                f"  URI: {redact_mongo_uri(uri)}\n"
                f"  Details: {exc}"
            ) from exc
        except ConfigurationError as exc:
            raise click.ClickException(
                f"MongoDB configuration error.\n"
                f"  URI: {redact_mongo_uri(uri)}\n"
                f"  Details: {exc}"
            ) from exc

        dbname = settings.mongo.db
        db = mongo_client[dbname]

        if dry_run:
            click.secho(
                "DRY RUN: would create indexes and counters (no changes).",
                fg="yellow",
            )
        else:
            ensure_business_indexes(db, drop_existing=drop_existing)
            seed_counters(db)

        t1 = time.perf_counter()
        click.secho("────────────────────────────────────────────", fg="cyan", bold=True)
        click.secho("Database Initialization Summary", fg="cyan", bold=True)
        click.secho("────────────────────────────────────────────", fg="cyan", bold=True)
        click.secho(f"  Database      : {dbname}")
        click.secho(f"  Drop existing : {'Yes' if drop_existing else 'No'}")
        click.secho(f"  Mode          : {'Dry run' if dry_run else 'Real run'}")
        click.secho(f"  Duration      : {t1 - t0:.2f} seconds")
        click.secho("────────────────────────────────────────────", fg="cyan", bold=True)
        sys.exit(0)

    finally:
        if mongo_client:
            mongo_client.close()
