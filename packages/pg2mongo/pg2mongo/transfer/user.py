from __future__ import annotations

from typing import Optional

import click
from pymongo import UpdateOne

from pg2mongo.builders.user_build import build_user_doc, user_insert_op
from pg2mongo import collections as cols
from pg2mongo.clients import connect_postgres, connect_mongo
from pg2mongo.cli.context import resolve_verbose, verbose_option
from pg2mongo.transfer.common import resolve_settings_from_ctx, close_connections_safe
from pg2mongo.transfer.progress import TransferProgress


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
@verbose_option
@click.pass_context
def user_cmd(
    ctx: click.Context,
    limit: Optional[int],
    dry_run: bool,
    verbose: int,
):
    """
    Transfer user records from Postgres → MongoDB (users collection).

    Insert-only: adds users that are missing in Mongo by Postgres id. Existing
    users are never updated or removed.
    """
    verbose = resolve_verbose(ctx, verbose)
    settings = resolve_settings_from_ctx(ctx, verbose=verbose)

    pg_conn = None
    mongo_client = None

    try:
        # 1) Connect to DBs
        pg_conn = connect_postgres(settings, verbose=verbose)
        mongo_client = connect_mongo(settings, verbose=verbose)

        db = mongo_client[settings.mongo.db]
        coll = db[cols.USERS]

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

        progress = TransferProgress(
            label="Users",
            total=total_rows,
            limit=limit or 0,
            verbose=verbose,
        )
        progress.announce()

        # 3) Build insert-only operations (skip existing users)
        ops: list[UpdateOne] = []
        with progress:
            for row in rows:
                doc = build_user_doc(row)
                branch = doc.get("branch") or {}
                hint = f"id={doc.get('_id')} userName={doc.get('userName')}"
                if progress.enabled(2):
                    hint += f" branch={branch.get('code', '')} active={doc.get('active')}"
                progress.step(hint, emit=verbose)

                if progress.enabled(4):
                    progress.secho(f"[user] doc={doc!r}", fg="white")

                ops.append(user_insert_op(doc))

        if dry_run:
            click.secho(
                f"[DRY-RUN] would insert up to {len(ops)} new users into "
                f"{cols.qualified(settings.mongo.db, cols.USERS)} "
                f"(existing users unchanged)",
                fg="yellow",
            )
            return

        # 4) Execute bulk_write
        result = coll.bulk_write(ops, ordered=False)

        inserted = len(result.upserted_ids)
        skipped = result.matched_count

        click.secho(
            (
                f"[users] Insert complete → "
                f"inserted={inserted}, "
                f"skipped_existing={skipped}"
            ),
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)
