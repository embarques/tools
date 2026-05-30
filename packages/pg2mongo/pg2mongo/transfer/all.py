from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import click

from pg2mongo.dates import parse_user_date
from pg2mongo.transfer.branch import branch_cmd
from pg2mongo.transfer.container import container_cmd
from pg2mongo.transfer.customer import customer_cmd
from pg2mongo.transfer.delivery import delivery_cmd
from pg2mongo.transfer.employee import employee_cmd
from pg2mongo.transfer.invoice import invoice_cmd
from pg2mongo.transfer.pickup import pickup_cmd
from pg2mongo.transfer.user import user_cmd


def _year_from_date(date_str: str) -> int:
    return parse_user_date(date_str).year


def _delivery_year_range(
    start_date: Optional[str],
    end_date: Optional[str],
) -> tuple[int, Optional[int]]:
    """Map CLI dates to delivery's year-based filter."""
    now_year = datetime.now(timezone.utc).year

    if start_date:
        start_year = _year_from_date(start_date)
    else:
        start_year = 2022

    if end_date:
        end_year = _year_from_date(end_date)
    elif start_date:
        end_year = now_year
    else:
        end_year = None

    return start_year, end_year


def _limit_for_optional(limit: int) -> Optional[int]:
    return limit if limit > 0 else None


def _build_invoke_kwargs(
    entity: str,
    *,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
    verbose: bool,
) -> dict[str, Any]:
    optional_limit = _limit_for_optional(limit)

    if entity in {"branch", "employee", "user"}:
        return {"limit": optional_limit, "dry_run": dry_run}

    if entity in {"customer", "pickup"}:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "dry_run": dry_run,
            "limit": limit,
        }

    if entity == "container":
        return {
            "start_date": start_date,
            "end_date": end_date,
            "limit": optional_limit,
            "dry_run": dry_run,
        }

    if entity == "invoice":
        return {
            "start_date": start_date,
            "end_date": end_date,
            "dry_run": dry_run,
            "limit": limit,
            "verbose": verbose,
        }

    if entity == "delivery":
        start_year, end_year = _delivery_year_range(start_date, end_date)
        kwargs: dict[str, Any] = {
            "start_year": start_year,
            "dry_run": dry_run,
            "limit": optional_limit,
        }
        if end_year is not None:
            kwargs["end_year"] = end_year
        return kwargs

    raise ValueError(f"Unknown entity: {entity}")


# Reference data first, then entities that depend on them.
TRANSFER_STEPS: list[tuple[str, click.Command]] = [
    ("branch", branch_cmd),
    ("employee", employee_cmd),
    ("user", user_cmd),
    ("customer", customer_cmd),
    ("container", container_cmd),
    ("invoice", invoice_cmd),
    ("pickup", pickup_cmd),
    ("delivery", delivery_cmd),
]


@click.command("all")
@click.option(
    "--start-date",
    help="Start date (YYYY-MM-DD or MM-DD-YYYY). If omitted, date-based entities resume from Mongo updatedAt.",
)
@click.option(
    "--end-date",
    help="End date (YYYY-MM-DD or MM-DD-YYYY). Defaults to today 23:59:59 UTC when start-date is set.",
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
    help="Limit records per entity (0 = no limit).",
)
@click.pass_context
def all_cmd(
    ctx: click.Context,
    start_date: Optional[str],
    end_date: Optional[str],
    dry_run: bool,
    limit: int,
):
    """
    Transfer all entities from Postgres to MongoDB in dependency order.

    Date-based entities (customer, container, invoice, pickup) use the same
    start/end date window as individual transfer commands. Deliveries map the
    date range to start/end years. Branch, employee, and user always run a full sync.
    """
    verbose = bool(ctx.obj.get("verbose", False))
    failed: list[str] = []

    click.secho("Starting full transfer (all entities)", fg="cyan", bold=True)
    if start_date or end_date:
        click.secho(
            f"  Date window: start={start_date or '(auto)'} end={end_date or '(today)'}",
            fg="cyan",
        )
    if dry_run:
        click.secho("  Mode: dry-run", fg="yellow")
    if limit:
        click.secho(f"  Limit: {limit} records per entity", fg="cyan")

    for entity, command in TRANSFER_STEPS:
        click.secho(f"\n{'─' * 60}", fg="cyan")
        click.secho(f"Transfer: {entity}", fg="cyan", bold=True)
        click.secho(f"{'─' * 60}", fg="cyan")

        kwargs = _build_invoke_kwargs(
            entity,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            limit=limit,
            verbose=verbose,
        )

        try:
            ctx.invoke(command, **kwargs)
        except Exception as exc:
            failed.append(entity)
            click.secho(f"❌ {entity} transfer failed: {exc}", fg="red", bold=True)
            if verbose:
                raise

    click.secho(f"\n{'═' * 60}", fg="cyan", bold=True)
    if failed:
        click.secho(
            f"Transfer all finished with errors in: {', '.join(failed)}",
            fg="red",
            bold=True,
        )
        raise click.ClickException(
            f"Transfer all completed with failures: {', '.join(failed)}"
        )

    click.secho("✅ Transfer all complete.", fg="green", bold=True)
