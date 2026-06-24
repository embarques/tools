from __future__ import annotations

import click

from pg2mongo.version import __version__
from pg2mongo.transfer.customer import customer_cmd
from pg2mongo.transfer.invoice import invoice_cmd
from pg2mongo.transfer.pickup import pickup_cmd
from pg2mongo.actions.init_indexes import init_indexes_cmd
from pg2mongo.actions.test_connection import test_connection_cmd
from pg2mongo.init_db import init_db_cmd
from pg2mongo.transfer.container import container_cmd
from pg2mongo.transfer.employee import employee_cmd
from pg2mongo.transfer.user import user_cmd
from pg2mongo.transfer.delivery import delivery_cmd
from pg2mongo.transfer.branch import branch_cmd
from pg2mongo.transfer.income_statement import income_statement_cmd
from pg2mongo.transfer.tables import tables_cmd
from pg2mongo.transfer.all import all_cmd






@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version=__version__, prog_name="pg2mongo")
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to db.toml (default: auto-discover db.toml in cwd or project root).",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbose output. Repeat for more detail, e.g. -vvvv.",
)
@click.pass_context
def cli(ctx: click.Context, config_path: str | None, verbose: int):
    """
    Postgres → MongoDB transfer toolkit.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["verbose"] = verbose


@cli.command("version")
def version_cmd():
    """Show pg2mongo version."""
    click.secho(f"pg2mongo {__version__}", fg="cyan")


@cli.group("transfer")
@click.pass_context
def transfer_group(ctx: click.Context):
    """Transfer commands per entity, or all at once."""
    pass


# Transfer subcommands
transfer_group.add_command(branch_cmd, name="branch")
transfer_group.add_command(employee_cmd, name="employee")
transfer_group.add_command(user_cmd, name="user")
transfer_group.add_command(customer_cmd, name="customer")
transfer_group.add_command(container_cmd, name="container")
transfer_group.add_command(income_statement_cmd, name="income-statement")
transfer_group.add_command(invoice_cmd, name="invoice")
transfer_group.add_command(pickup_cmd, name="pickup")
transfer_group.add_command(delivery_cmd, name="delivery")
transfer_group.add_command(tables_cmd, name="tables")
transfer_group.add_command(all_cmd, name="all")


# Admin / utility
cli.add_command(init_indexes_cmd, name="init-indexes")
cli.add_command(init_db_cmd, name="init-db")
cli.add_command(test_connection_cmd, name="test-connection")


def main():
    cli(prog_name="pg2mongo")


if __name__ == "__main__":
    main()
