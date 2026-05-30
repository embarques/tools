from __future__ import annotations

from typing import Callable, TypeVar

import click

F = TypeVar("F", bound=Callable[..., object])


def get_config_path(ctx: click.Context) -> str | None:
    """Walk up the Click context chain for ``config_path`` (supports ``ctx.invoke``)."""
    current: click.Context | None = ctx
    while current is not None:
        if current.obj:
            path = current.obj.get("config_path")
            if path:
                return path
        current = current.parent
    return None


def get_verbose(ctx: click.Context) -> bool:
    """Return whether verbose mode is enabled anywhere in the Click context chain."""
    current: click.Context | None = ctx
    while current is not None:
        if current.obj and current.obj.get("verbose"):
            return True
        current = current.parent
    return False


def resolve_verbose(ctx: click.Context, verbose: bool) -> bool:
    """Apply a command-level ``-v`` flag and return the effective verbose state."""
    if verbose:
        ctx.ensure_object(dict)
        ctx.obj["verbose"] = True
    return get_verbose(ctx)


def verbose_option(func: F) -> F:
    """Click decorator: add ``-v / --verbose`` to a command."""
    return click.option(
        "-v",
        "--verbose",
        is_flag=True,
        help="Enable verbose output.",
    )(func)
