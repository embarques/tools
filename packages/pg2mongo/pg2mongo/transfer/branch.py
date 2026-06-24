from __future__ import annotations

from typing import Optional

import click
from pymongo import UpdateOne

from pg2mongo.builders.branch_build import build_branch_doc
from pg2mongo import collections as cols
from pg2mongo.clients import connect_postgres, connect_mongo
from pg2mongo.cli.context import resolve_verbose, verbose_option
from pg2mongo.transfer.common import resolve_settings_from_ctx, close_connections_safe
from pg2mongo.transfer.progress import TransferProgress


BRANCH_SQL = """
SELECT
    id,
    name,
    code,
    b_type,
    address1 AS "address.address1",
    address2 AS "address.address2",
    city     AS "address.city",
    zipcode  AS "address.zipcode",
    country  AS "address.country",
    phone1,
    phone2,
    disclaimer,
    branch."prefix"               AS prefix,
    branch.logo                   AS logo,
    branch.default_label_status   AS default_label_status
FROM branch
ORDER BY id
"""


@click.command("branch")
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
def branch_cmd(
    ctx: click.Context,
    limit: Optional[int],
    dry_run: bool,
    verbose: int,
):
    """
    Transfer branch records from Postgres → MongoDB (branches collection).
    """
    verbose = resolve_verbose(ctx, verbose)
    settings = resolve_settings_from_ctx(ctx, verbose=verbose)

    pg_conn = None
    mongo_client = None

    try:
        # 1) Connect DBs
        pg_conn = connect_postgres(settings, verbose=verbose)
        mongo_client = connect_mongo(settings, verbose=verbose)

        db = mongo_client[settings.mongo.db]
        coll = db[cols.BRANCHES]

        if verbose:
            click.secho("[branches] Executing Postgres query…", fg="cyan")

        # 2) Run query
        with pg_conn.cursor() as cur:
            cur.execute(BRANCH_SQL)
            rows = cur.fetchall()

        total_rows = len(rows)
        if total_rows == 0:
            click.secho("[branches] No records found in branch table.", fg="yellow")
            return

        if limit is not None:
            rows = rows[:limit]

        if verbose:
            msg = f"[branches] Retrieved {len(rows)} rows from Postgres"
            if limit is not None:
                msg += f" (limit={limit})"
            click.secho(msg, fg="cyan")

        progress = TransferProgress(
            label="Branches",
            total=total_rows,
            limit=limit or 0,
            verbose=verbose,
        )
        progress.announce()

        # 3) Build bulk upsert operations
        ops: list[UpdateOne] = []
        with progress:
            for row in rows:
                doc = build_branch_doc(row)
                hint = f"id={doc.get('_id')} code={doc.get('code')} name={doc.get('name')}"
                if progress.enabled(2):
                    hint += f" phone1={doc.get('phone1', '')}"
                progress.step(hint, emit=verbose)

                if progress.enabled(4):
                    progress.secho(f"[branch] doc={doc!r}", fg="white")

                ops.append(
                    UpdateOne(
                        {"_id": doc["_id"]},
                        {
                            "$set": doc,
                            "$unset": {
                                "phone1": "",
                                "phone2": "",
                                "created": "",
                            },
                        },
                        upsert=True,
                    )
                )

        if dry_run:
            click.secho(
                f"[DRY-RUN] would upsert {len(ops)} documents into "
                f"{cols.qualified(settings.mongo.db, cols.BRANCHES)}",
                fg="yellow",
            )
            return

        # 4) Execute bulk_write
        result = coll.bulk_write(ops, ordered=False)

        click.secho(
            (
                f"[branches] Upsert complete → "
                f"matched={result.matched_count}, "
                f"modified={result.modified_count}, "
                f"upserted={len(result.upserted_ids)}"
            ),
            fg="green",
        )

    finally:
        close_connections_safe(pg_conn, mongo_client)
