from __future__ import annotations

from typing import Optional

import click
from pymongo import UpdateOne

from pg2mongo.builders.user_build import build_user_doc
from pg2mongo.clients import connect_postgres, connect_mongo
from pg2mongo.transfer.common import resolve_settings, close_connections_safe


USER_SQL = """
SELECT
    u.id,
    u.username,
    u.first_name AS full_name,
    u.date_joined AS time_created,
    COALESCE(p.register_key, ''::character varying) AS register_key,
    COALESCE(p.temp_key, ''::character varying)     AS temp_key,
    COALESCE(p.branch_id, 0)                        AS branch_id
FROM auth_user u
LEFT JOIN user_profile p
    ON p.user_id = u."id"
ORDER BY u.id
"""


@click.command("user")
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
def user_cmd(
    ctx: click.Context,
    limit: Optional[int],
    dry_run: bool,
):
    """
    Transfer user records from Postgres → MongoDB (users collection).
    """
    config_path = ctx.obj.get("config_path")
    verbose = bool(ctx.obj.get("verbose"))

    settings = resolve_settings(config_path, verbose)

    pg_conn = None
    mongo_client = None

    try:
        # 1) Connect to DBs
        pg_conn = connect_postgres(settings, verbose=verbose)
        mongo_client = connect_mongo(settings, verbose=verbose)

        db = mongo_client[settings.mongo.db]
        coll = db["users"]

        # 2) Run query against Postgres
        if verbose:
            click.secho("[users] Executing Postgres query…", fg="cyan")

        with pg_conn.cursor() as cur:
            cur.execute(USER_SQL)
            rows = cur.fetchall()

        total_rows = len(rows)
        if total_rows == 0:
            click.secho("[users] No records found in auth_user.", fg="yellow")
            return

        if limit is not None:
            rows = rows[:limit]

        if verbose:
            msg = f"[users] Retrieved {len(rows)} rows from Postgres"
            if limit is not None:
                msg += f" (limit={limit})"
            click.secho(msg, fg="cyan")

        # 3) Build bulk upsert operations
        ops: list[UpdateOne] = []
        for idx, row in enumerate(rows, start=1):
            doc = build_user_doc(row)

            if dry_run and verbose:
                click.secho(
                    f"[users] DRY-RUN {idx}/{len(rows)} _id={doc['_id']} userName={doc['userName']}",
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
                f"[DRY-RUN] users: would upsert {len(ops)} documents into {settings.mongo.db}.users",
                fg="yellow",
            )
            return

        # 4) Execute bulk_write
        result = coll.bulk_write(ops, ordered=False)

        click.secho(
            (
                f"[users] Upsert complete → "
                f"matched={result.matched_count}, "
                f"modified={result.modified_count}, "
                f"upserted={len(result.upserted_ids)}"
            ),
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)
