from __future__ import annotations

from typing import Optional

import click

from pg2mongo.cli.context import resolve_verbose, verbose_option
from pg2mongo.table_import import import_table, parse_table_list, resolve_table_specs
from pg2mongo.transfer.common import (
    close_connections_safe,
    connect_postgres_and_mongo,
    resolve_settings_from_ctx,
)


@click.command("tables")
@click.option(
    "--tables",
    "-t",
    required=True,
    help="Comma-separated Postgres table names (e.g. city,invoice_description).",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of records per table (for testing).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview actions without writing to Mongo.",
)
@verbose_option
@click.pass_context
def tables_cmd(
    ctx: click.Context,
    tables: str,
    limit: Optional[int],
    dry_run: bool,
    verbose: int,
):
    """
    Import small Postgres lookup tables into MongoDB.

    Collection names follow Mongo conventions (e.g. city → cities,
    invoice_description → invoice_descriptions).
    """
    verbose = resolve_verbose(ctx, verbose)
    settings = resolve_settings_from_ctx(ctx, verbose=verbose)
    table_names = parse_table_list(tables)
    specs = resolve_table_specs(table_names)

    pg_conn = None
    mongo_client = None

    try:
        pg_conn, mongo_client = connect_postgres_and_mongo(settings, verbose)
        db = mongo_client[settings.mongo.db]

        for spec in specs:
            click.secho(
                f"\nImport: {spec.pg_table} → {spec.mongo_collection}",
                fg="cyan",
                bold=True,
            )
            stats = import_table(
                pg_conn,
                db,
                spec,
                dry_run=dry_run,
                limit=limit,
                verbose=verbose,
            )
            if not dry_run:
                click.secho(
                    f"[{spec.pg_table}] Done → matched={stats['matched']} "
                    f"modified={stats['modified']} upserted={stats['upserted']}",
                    fg="green",
                )

        click.secho("\n✅ Table import complete.", fg="green", bold=True)

    finally:
        close_connections_safe(pg_conn, mongo_client)
