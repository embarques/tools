from __future__ import annotations

from typing import Tuple

import click
import psycopg
from psycopg.rows import dict_row
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

from pg2mongo.config import Settings


def connect_postgres(settings: Settings, verbose: bool = False) -> psycopg.Connection:
    pg = settings.postgres
    try:
        conn = psycopg.connect(
            host=pg.server,
            port=pg.port,
            dbname=pg.db,
            user=pg.username,
            password=pg.password,
            row_factory=dict_row,
        )
        if verbose:
            click.secho(
                f"Postgres connected → host={pg.server} db={pg.db} schema={pg.schema_name}",
                fg="green",
            )
        return conn
    except Exception as exc:
        click.secho("❌ Failed to connect to Postgres:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
        raise


def connect_mongo(settings: Settings, verbose: bool = False) -> MongoClient:
    mg = settings.mongo
    uri = mg.build_uri()
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
        if verbose:
            click.secho(f"Mongo connected → {uri}", fg="green")
            click.secho(
                f"Mongo target → db={mg.db}",
                fg="green",
            )
        return client
    except OperationFailure as exc:
        click.secho("❌ Mongo authentication/authorization failed:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
        raise
    except PyMongoError as exc:
        click.secho("❌ Mongo connection error:", fg="red", bold=True)
        click.secho(str(exc), fg="red")
        raise


def close_connections(pg_conn, mongo_client):
    try:
        if pg_conn:
            pg_conn.close()
    except Exception:
        pass
    try:
        if mongo_client:
            mongo_client.close()
    except Exception:
        pass
