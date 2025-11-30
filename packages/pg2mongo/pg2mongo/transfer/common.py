from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple, Optional

import click
from pymongo import MongoClient

from pg2mongo.config import load_settings, Settings
from pg2mongo.clients import connect_postgres, connect_mongo, close_connections
from pg2mongo.dates import inclusive_window, parse_user_date


DEFAULT_START_DATE = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def resolve_settings(config_path: str | None, verbose: bool) -> Settings:
    settings = load_settings(config_path)
    if verbose:
        click.secho(
            f"Using {'config file' if config_path else 'environment'}: "
            f"{config_path or 'ENV'}",
            fg="cyan",
        )
        click.secho(
            f"[DEBUG] Postgres DB: {settings.postgres.db} | Mongo DB: {settings.mongo.db}",
            fg="cyan",
        )
    return settings


def connect_postgres_and_mongo(
    settings: Settings,
    verbose: bool,
):
    pg_conn = connect_postgres(settings, verbose=verbose)
    mongo_client = connect_mongo(settings, verbose=verbose)
    return pg_conn, mongo_client


def _max_updated_at(
    mongo_client: MongoClient,
    db_name: str,
    collection: str,
) -> Optional[datetime]:
    cursor = (
        mongo_client[db_name][collection]
        .find({}, {"updatedAt": 1})
        .sort("updatedAt", -1)
        .limit(1)
    )
    doc = next(cursor, None)
    if not doc:
        return None

    ts = doc.get("updatedAt")
    if isinstance(ts, datetime):
        if ts.tzinfo:
            return ts.astimezone(timezone.utc)
        return ts.replace(tzinfo=timezone.utc)
    return None


def get_date_window(
    mongo_client: MongoClient,
    settings: Settings,
    start_date: str | None,
    end_date: str | None,
    verbose: bool,
    *,
    collection: str,
) -> Tuple[str, str]:
    """
    Returns (start_iso, end_iso) for Postgres WHERE ... BETWEEN SYMMETRIC.
    Logic:
      - If --start-date supplied → inclusive_window(start, end).
      - Else:
          • If Mongo has data → max(updatedAt).
          • Else → DEFAULT_START_DATE.
      - end_date defaults to today 23:59:59 UTC.
    """

    if start_date:
        start_iso, end_iso = inclusive_window(start_date, end_date)
        if verbose:
            click.secho(
                f"Date window (from args): {start_iso} → {end_iso}",
                fg="magenta",
            )
        return start_iso, end_iso

    last = _max_updated_at(mongo_client, settings.mongo.db, collection)

    if last:
        start_dt = last
        src = f"mongo {settings.mongo.db}.{collection}.updatedAt"
    else:
        start_dt = DEFAULT_START_DATE
        src = f"default={DEFAULT_START_DATE.date().isoformat()}"

    if end_date:
        end_dt = parse_user_date(end_date).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    else:
        now = datetime.now(timezone.utc)
        end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_iso = start_dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    end_iso = end_dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")

    if verbose:
        click.secho(
            f"Date window (auto from {src}): {start_iso} → {end_iso}",
            fg="magenta",
        )

    return start_iso, end_iso


def close_connections_safe(pg_conn, mongo_client):
    close_connections(pg_conn, mongo_client)
