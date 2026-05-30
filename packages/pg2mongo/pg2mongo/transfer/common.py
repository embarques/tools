from __future__ import annotations

from datetime import datetime, date, time, timezone
from typing import Tuple, Optional

import click
from pymongo import MongoClient

from pg2mongo.config import load_settings, Settings, resolve_config_path
from pg2mongo.cli.context import get_config_path, get_verbose
from pg2mongo.clients import connect_postgres, connect_mongo, close_connections
from pg2mongo.dates import inclusive_window, parse_user_date


DEFAULT_START_DATE = date(2022, 1, 1)


def resolve_settings_from_ctx(ctx: click.Context, verbose: bool = False) -> Settings:
    """Load settings using config_path / verbose from the Click context chain."""
    config_path = get_config_path(ctx)
    verbose = verbose or get_verbose(ctx)
    return resolve_settings(config_path, verbose)


def resolve_settings(config_path: str | None, verbose: bool) -> Settings:
    path = resolve_config_path(config_path)
    settings = load_settings(str(path))
    if verbose:
        click.secho(f"Using config file: {path}", fg="cyan")
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


def _parse_date_str(value: str | None) -> datetime | None:
    """Accepts YYYY-MM-DD or MM-DD-YYYY and returns a UTC datetime at midnight."""
    if not value:
        return None

    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m-%d-%Y"):
        try:
            d = datetime.strptime(value, fmt).date()
            return datetime.combine(d, time.min).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: {value!r}. Use YYYY-MM-DD or MM-DD-YYYY.")


def get_last_processed_timestamp(coll, field: str = "updatedAt") -> datetime | None:
    """Read the last processed timestamp from Mongo, or None if empty."""
    doc = coll.find_one(
        {field: {"$exists": True}},
        sort=[(field, -1)],
        projection={field: 1},
    )
    if not doc:
        return None
    ts = doc.get(field)
    if isinstance(ts, datetime):
        # ensure it is timezone-aware
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    return None


def get_date_window(
    coll,
    start_date: str | None,
    end_date: str | None,
    verbose: bool = False,
) -> tuple[str, str]:
    """
    Compute the Postgres start/end timestamps as strings.

    Priority:
      1) If start_date provided -> use that.
      2) Else use last updatedAt from Mongo.
      3) Else fallback to DEFAULT_START_DATE (2022-01-01).

    End:
      - If end_date provided -> that day 23:59:59.999999
      - Else -> today 23:59:59.999999 UTC
    """
    now = datetime.now(timezone.utc)

    # ---- START DATE ----
    if start_date:
        start_dt = _parse_date_str(start_date)
    else:
        last_ts = get_last_processed_timestamp(coll, "updatedAt")
        if last_ts:
            start_dt = last_ts
        else:
            # First run / empty collection -> use default
            start_dt = datetime.combine(DEFAULT_START_DATE, time.min).replace(
                tzinfo=timezone.utc
            )

    # ---- END DATE ----
    if end_date:
        end_dt = _parse_date_str(end_date)
        # move to end of day
        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999_999)
    else:
        # today end-of-day UTC
        end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999_999)

    if verbose:
        click.secho(
            f"Date window: {start_dt} → {end_dt}",
            fg="green",
        )

    # Format for Postgres (TIMESTAMPTZ literal)
    start_iso = start_dt.strftime("%Y-%m-%d %H:%M:%S%z")
    end_iso = end_dt.strftime("%Y-%m-%d %H:%M:%S%z")
    return start_iso, end_iso

def close_connections_safe(pg_conn, mongo_client):
    close_connections(pg_conn, mongo_client)
