from __future__ import annotations

from typing import Optional

import click

from pg2mongo import collections as cols
from pg2mongo.cli.context import resolve_verbose, verbose_option
from pg2mongo.mongo import get_collection
from pg2mongo.builders.income_statement_sync import (
    INCOME_STATEMENT_COUNT_SQL,
    sync_income_statements_in_window,
)
from pg2mongo.transfer.common import (
    resolve_settings_from_ctx,
    connect_postgres_and_mongo,
    get_date_window,
    close_connections_safe,
)
from pg2mongo.transfer.progress import TransferProgress, count_sql_rows


@click.command("income-statement")
@click.option(
    "--start-date",
    help="Start date (YYYY-MM-DD or MM-DD-YYYY). If omitted, auto from Mongo updatedAt.",
)
@click.option(
    "--end-date",
    help="End date (YYYY-MM-DD or MM-DD-YYYY). Defaults to today 23:59:59 UTC.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview actions without writing to Mongo.",
)
@click.option(
    "--limit",
    type=int,
    default=0,
    help="Limit number of records processed (0 = no limit).",
)
@verbose_option
@click.pass_context
def income_statement_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
    verbose: int,
):
    """Transfer income statements from Postgres ``income_statement`` to MongoDB."""
    verbose = resolve_verbose(ctx, verbose)
    settings = resolve_settings_from_ctx(ctx, verbose=verbose)
    pg_conn = None
    mongo_client = None

    try:
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)
        coll = get_collection(mongo_client, settings.mongo.db, cols.INCOME_STATEMENTS)

        start_iso, end_iso = get_date_window(
            coll,
            start_date,
            end_date,
            verbose,
        )

        total = count_sql_rows(pg_conn, INCOME_STATEMENT_COUNT_SQL, (start_iso, end_iso))
        progress = TransferProgress(
            label="Income statements",
            total=total,
            limit=limit,
            verbose=verbose,
        )
        progress.announce()

        with progress:
            processed = sync_income_statements_in_window(
                pg_conn,
                mongo_client,
                settings.mongo.db,
                start_iso,
                end_iso,
                dry_run=dry_run,
                verbose=verbose,
                limit=limit,
                progress=progress,
            )

        click.secho(
            f"✅ Income statement transfer complete. "
            f"{progress.summary(dry_run=dry_run)}, "
            f"dry_run={dry_run}",
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)
