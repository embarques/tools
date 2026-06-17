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
    return get_verbosity(ctx) > 0


def get_verbosity(ctx: click.Context) -> int:
    """Return the accumulated verbosity level from the Click context chain."""
    level = 0
    current: click.Context | None = ctx
    while current is not None:
        if current.obj:
            value = current.obj.get("verbose", 0)
            if isinstance(value, bool):
                level += int(value)
            else:
                level += int(value or 0)
        current = current.parent
    return level


def resolve_verbose(ctx: click.Context, verbose: int | bool) -> int:
    """Apply a command-level ``-v`` flag and return the effective verbosity level."""
    if verbose:
        ctx.ensure_object(dict)
        ctx.obj["verbose"] = int(verbose)
    return get_verbosity(ctx)


def verbose_option(func: F) -> F:
    """Click decorator: add repeatable ``-v / --verbose`` to a command."""
    return click.option(
        "-v",
        "--verbose",
        count=True,
        help="Increase verbose output. Repeat for more detail, e.g. -vvvv.",
    )(func)
