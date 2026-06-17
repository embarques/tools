from __future__ import annotations

import click
from pymongo.errors import PyMongoError

from pg2mongo.cli.context import get_config_path, resolve_verbose, verbose_option
from pg2mongo.transfer.common import (
    resolve_settings,
    close_connections_safe,
)
from pg2mongo.clients import connect_postgres, connect_mongo


@click.command("test-connection")
@verbose_option
@click.pass_context
def test_connection_cmd(ctx: click.Context, verbose: int):
    """
    Test and validate connection to Postgres and MongoDB.
    Prints connection status and database names.
    """
    verbose = resolve_verbose(ctx, verbose)
    config_path = get_config_path(ctx)

    settings = resolve_settings(config_path, verbose)

    pg_conn = None
    mongo_client = None

    click.secho("🔌 Testing database connections…", fg="cyan", bold=True)

    # -------------------------------------------------------------
    # Test Postgres
    # -------------------------------------------------------------
    click.secho("\nPostgres:", fg="yellow", bold=True)
    try:
        # Avoid duplicate "Postgres connected → ..." from connect_postgres
        pg_conn = connect_postgres(settings, verbose=False)

        with pg_conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok;")
            result = cur.fetchone()  # dict_row → {"ok": 1}

        ok_value = None
        if isinstance(result, dict):
            ok_value = result.get("ok")
        else:
            ok_value = result

        click.secho("  ✓ Connected successfully", fg="green")
        click.secho(
            f"  • Host: {settings.postgres.server}:{settings.postgres.port}",
            fg="white",
        )
        click.secho(f"  • Database: {settings.postgres.db}", fg="white")
        click.secho(f"  • Schema: {settings.postgres.schema_name}", fg="white")
        click.secho(f"  • Ping Result: {ok_value}", fg="white")
    except Exception as exc:
        click.secho("  ✗ Postgres connection failed:", fg="red", bold=True)
        click.secho(f"    {exc}", fg="red")

    # -------------------------------------------------------------
    # Test MongoDB
    # -------------------------------------------------------------
    click.secho("\nMongoDB:", fg="yellow", bold=True)
    try:
        # Avoid duplicate prints inside connect_mongo
        mongo_client = connect_mongo(settings, verbose=False)

        # Explicit ping for clarity
        mongo_client.admin.command("ping")

        click.secho("  ✓ Connected successfully", fg="green")
        click.secho(
            f"  • Database: {settings.mongo.db}",
            fg="white",
        )
    except PyMongoError as exc:
        click.secho("  ✗ MongoDB connection failed:", fg="red", bold=True)
        click.secho(f"    {exc}", fg="red")
    except Exception as exc:
        click.secho("  ✗ MongoDB connection error:", fg="red", bold=True)
        click.secho(f"    {exc}", fg="red")

    # -------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------
    close_connections_safe(pg_conn, mongo_client)
    click.secho("\nDone.\n", fg="cyan", bold=True)
