from __future__ import annotations

import click


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


def get_verbose(ctx: click.Context, *, local: bool = False) -> bool:
    """
    Return whether verbose mode is enabled.

    *local* — when True, only check the current context (e.g. invoice ``-v`` flag
    is handled separately by the caller).
    """
    current: click.Context | None = ctx if local else ctx
    while current is not None:
        if current.obj and current.obj.get("verbose"):
            return True
        if local:
            break
        current = current.parent
    return False
