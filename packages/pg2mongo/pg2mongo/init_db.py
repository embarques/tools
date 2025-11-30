from __future__ import annotations
import sys
import time
from urllib.parse import urlparse

import click
from pymongo import MongoClient
from pymongo.errors import (
    OperationFailure,
    ConfigurationError,
    ServerSelectionTimeoutError,
    InvalidURI,
)

from pg2mongo.settings import load_settings, load_settings_from_dict
from pg2mongo.config import load_db_config, dbconfig_to_settings_dict
from pg2mongo.admin import ensure_business_indexes, seed_counters
from pg2mongo.transfer.common import _redact_mongo_uri


@click.command("init-db")
@click.option("--config", "config_path", type=click.Path(exists=True, dir_okay=False), default=None)
@click.option("--db", "db_override", type=str, default=None)
@click.option("--drop-existing", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--verbose", is_flag=True)
def init_db_cmd(config_path: str | None, db_override: str | None,
                drop_existing: bool, dry_run: bool, verbose: bool) -> None:
    """Initialize MongoDB: ensure indexes and seed counters (idempotent)."""
    # ---- load settings ----
    if config_path:
        cfg = load_db_config(config_path)
        settings = load_settings_from_dict(dbconfig_to_settings_dict(cfg))
        if verbose:
            click.secho(f"Using config file: {config_path}", fg="green")
    else:
        settings = load_settings()
        if verbose:
            click.secho("Using environment variables", fg="green")

    mongo_client = None
    try:
        t0 = time.perf_counter()

        # ---- friendly connect + ping ----
        try:
            mongo_client = MongoClient(settings.mongo_uri)
            mongo_client.admin.command("ping")
        except InvalidURI as e:
            raise click.ClickException(
                f"MongoDB connection failed: Invalid URI.\n"
                f"  URI: {_redact_mongo_uri(settings.mongo_uri)}\n"
                f"  Details: {e}"
            )
        except OperationFailure as e:
            parsed = urlparse(settings.mongo_uri)
            user = (parsed.username or "").strip()
            query = dict(kv.split("=", 1) for kv in parsed.query.split("&") if "=" in kv) if parsed.query else {}
            auth_source = query.get("authSource", "<default>")
            mech = query.get("authMechanism", "<default>")
            code = getattr(e, "code", None)
            code_name = getattr(e, "details", {}).get("codeName") if getattr(e, "details", None) else None
            raise click.ClickException(
                f"MongoDB authentication failed.\n"
                f"  URI: {_redact_mongo_uri(settings.mongo_uri)}\n"
                f"  Username: {user or '<none>'}\n"
                f"  authSource: {auth_source}\n"
                f"  authMechanism: {mech}\n"
                f"  Error: {str(e)}\n"
                f"  Code: {code or '<n/a>'} ({code_name or 'AuthenticationFailed'})\n"
            )
        except ServerSelectionTimeoutError as e:
            raise click.ClickException(
                f"MongoDB server selection timed out.\n"
                f"  URI: {_redact_mongo_uri(settings.mongo_uri)}\n"
                f"  Details: {e}"
            )
        except ConfigurationError as e:
            raise click.ClickException(
                f"MongoDB configuration error.\n"
                f"  URI: {_redact_mongo_uri(settings.mongo_uri)}\n"
                f"  Details: {e}"
            )
        except Exception as e:
            raise click.ClickException(
                f"MongoDB connection failed with an unexpected error.\n"
                f"  URI: {_redact_mongo_uri(settings.mongo_uri)}\n"
                f"  Details: {e}"
            )

        dbname = db_override or settings.mongo_db
        db = mongo_client[dbname]
        if verbose:
            click.secho(f"Mongo DB: {dbname} ({_redact_mongo_uri(settings.mongo_uri)})", fg="green")

        # ---- work ----
        if dry_run:
            click.secho("DRY RUN: would create indexes and counters (no changes).", fg="yellow")
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
        try:
            if mongo_client:
                mongo_client.close()
        except Exception:
            pass
