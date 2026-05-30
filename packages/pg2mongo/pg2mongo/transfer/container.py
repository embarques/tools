from __future__ import annotations

from datetime import datetime, date, time, timezone
from typing import Optional

import click
from pymongo import UpdateOne

from pg2mongo.builders.container_build import build_container_doc
from pg2mongo import collections as cols
from pg2mongo.clients import connect_postgres, connect_mongo
from pg2mongo.transfer.common import resolve_settings, close_connections_safe


CONTAINER_SQL = """
SELECT
    id,
    designation,
    COALESCE(booking_number, '')   AS booking_number,
    COALESCE(container_number, '') AS container_number,
    COALESCE(broker, '')           AS broker,
    COALESCE(trans_company, '')    AS trans_company,
    cost,
    departure_date,
    arrival_date,
    time_created,
    time_modified
FROM container
WHERE time_modified BETWEEN SYMMETRIC %s AND %s
ORDER BY id
"""


def _parse_cli_date(value: str) -> datetime:
    """
    Accepts:
      - YYYY-MM-DD
      - MM-DD-YYYY
    Returns a UTC datetime at 00:00:00.
    """
    value = value.strip()
    parts = value.split("-")
    if len(parts[0]) == 4:
        # YYYY-MM-DD
        dt = datetime.strptime(value, "%Y-%m-%d")
    else:
        # MM-DD-YYYY
        dt = datetime.strptime(value, "%m-%d-%Y")

    return dt.replace(tzinfo=timezone.utc)


def _default_start_datetime() -> datetime:
    # Your global default start (same as we used in docs): 2022-01-01
    return datetime(2022, 1, 1, tzinfo=timezone.utc)


def _end_of_day(dt: datetime) -> datetime:
    return datetime.combine(
        dt.date(),
        time(23, 59, 59, 999999, tzinfo=timezone.utc),
    )


def _determine_date_window_for_containers(
    coll,
    cli_start: Optional[str],
    cli_end: Optional[str],
    verbose: bool,
) -> tuple[datetime, datetime]:
    """
    Compute [start, end] window:

    - If cli_start is provided, use that.
    - Else, use last updatedAt from Mongo containers.
    - If collection is empty, fall back to 2022-01-01.

    - If cli_end is provided, use that (end-of-day).
    - Else, use today (UTC) end-of-day.
    """
    # Start datetime
    if cli_start:
        start_dt = _parse_cli_date(cli_start)
    else:
        # Look up last updatedAt in Mongo
        last_doc = (
            coll.find({"updatedAt": {"$type": "date"}})
            .sort("updatedAt", -1)
            .limit(1)
        )
        last: Optional[datetime] = None
        for doc in last_doc:
            last = doc.get("updatedAt")
            break

        if last is not None and isinstance(last, (datetime, date)):
            if isinstance(last, date) and not isinstance(last, datetime):
                # convert date -> datetime
                last = datetime.combine(last, time(0, 0, tzinfo=timezone.utc))
            start_dt = last
            if verbose:
                click.secho(
                    f"[containers] Using last Mongo updatedAt as start-date: {start_dt.isoformat()}",
                    fg="cyan",
                )
        else:
            start_dt = _default_start_datetime()
            if verbose:
                click.secho(
                    f"[containers] No existing docs, using default start-date: {start_dt.date()}",
                    fg="cyan",
                )

    # End datetime
    if cli_end:
        end_raw = _parse_cli_date(cli_end)
        end_dt = _end_of_day(end_raw)
    else:
        now_utc = datetime.now(timezone.utc)
        end_dt = _end_of_day(now_utc)

    return start_dt, end_dt


@click.command("container")
@click.option(
    "--start-date",
    type=str,
    default=None,
    help="Start date (YYYY-MM-DD or MM-DD-YYYY). If omitted, uses last updatedAt in Mongo.",
)
@click.option(
    "--end-date",
    type=str,
    default=None,
    help="End date (YYYY-MM-DD or MM-DD-YYYY). Defaults to today (UTC).",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of records processed (for testing).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview actions without writing to Mongo.",
)
@click.pass_context
def container_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    limit: Optional[int],
    dry_run: bool,
):
    """
    Transfer container records from Postgres → MongoDB (containers collection).
    """
    config_path = ctx.obj.get("config_path")
    verbose = bool(ctx.obj.get("verbose"))

    settings = resolve_settings(config_path, verbose)

    pg_conn = None
    mongo_client = None

    try:
        # 1) Connect to DBs (same style as invoice/pickup)
        pg_conn = connect_postgres(settings, verbose=verbose)
        mongo_client = connect_mongo(settings, verbose=verbose)

        db = mongo_client[settings.mongo.db]
        coll = db[cols.CONTAINERS]

        # 2) Determine date window (uses updatedAt when start_date is None)
        start_dt, end_dt = _determine_date_window_for_containers(
            coll=coll,
            cli_start=start_date,
            cli_end=end_date,
            verbose=verbose,
        )

        if verbose:
            click.secho(
                f"[containers] Date window: {start_dt.isoformat()} → {end_dt.isoformat()}",
                fg="cyan",
            )

        # 3) Run query against Postgres
        with pg_conn.cursor() as cur:
            cur.execute(CONTAINER_SQL, (start_dt, end_dt))
            rows = cur.fetchall()

        total_rows = len(rows)
        if total_rows == 0:
            click.secho("[containers] No records found for given date range.", fg="yellow")
            return

        if limit is not None:
            rows = rows[:limit]

        # 4) Build bulk upsert operations
        ops: list[UpdateOne] = []
        for idx, row in enumerate(rows, start=1):
            doc = build_container_doc(row)

            if dry_run and verbose:
                click.secho(
                    f"[containers] DRY-RUN {idx}/{total_rows} _id={doc['_id']} name={doc['name']}",
                    fg="white",
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
                f"[DRY-RUN] containers: would upsert {len(ops)} documents into {settings.mongo.db}.containers",
                fg="yellow",
            )
            return

        # 5) Execute bulk_write
        result = coll.bulk_write(ops, ordered=False)

        click.secho(
            (
                f"[containers] Upsert complete → "
                f"matched={result.matched_count}, "
                f"modified={result.modified_count}, "
                f"upserted={len(result.upserted_ids)}"
            ),
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)
