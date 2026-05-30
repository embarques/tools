from __future__ import annotations

import sys
from typing import Optional

import click


def count_sql_rows(pg_conn, sql: str, params: tuple | list) -> int:
    """Run a ``SELECT COUNT(*)`` (or ``cnt`` alias) and return the integer total."""
    with pg_conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if not row:
        return 0
    if isinstance(row, dict):
        if "cnt" in row:
            return int(row["cnt"])
        return int(next(iter(row.values())))
    return int(row[0])


def format_progress(current: int, total: int) -> str:
    """Human-readable ``[current/total] (pct%)`` fragment."""
    if total <= 0:
        return f"[{current}]"
    pct = (current / total) * 100
    return f"[{current}/{total}] ({pct:.1f}%)"


class TransferProgress:
    """
    Progress reporting for long-running Postgres → Mongo transfers.

    * Non-verbose: Click progress bar with position, percent, and ETA.
    * Verbose: each line prefixed with ``[current/total] (pct%)``.
    """

    def __init__(
        self,
        *,
        label: str,
        total: Optional[int],
        limit: int = 0,
        verbose: bool = False,
    ) -> None:
        self.label = label
        self.total = total
        self.limit = limit
        self.verbose = verbose
        self.current = 0
        self._target = self._effective_target()
        self._bar: click.progressbar | None = None

    def _effective_target(self) -> Optional[int]:
        if self.total is None:
            return None
        if self.limit > 0:
            return min(self.limit, self.total)
        return self.total

    def announce(self) -> None:
        """Print how many records will be processed before the main loop."""
        if self._target is not None:
            limit_note = ""
            if self.limit > 0 and self.total is not None and self.limit < self.total:
                limit_note = f" (limit {self.limit:,})"
            click.secho(
                f"{self.label}: {self._target:,} of {self.total:,} record(s) to process{limit_note}",
                fg="cyan",
                bold=True,
            )
            return
        click.secho(f"{self.label}: processing records…", fg="cyan", bold=True)

    def prefix(self) -> str:
        if self._target:
            return format_progress(self.current, self._target)
        return f"[{self.current}]"

    def __enter__(self) -> TransferProgress:
        if not self.verbose and self._target and self._target > 0:
            self._bar = click.progressbar(
                length=self._target,
                label=self.label,
                show_eta=True,
                show_percent=True,
                show_pos=True,
            )
            self._bar.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._bar is not None:
            self._bar.__exit__(exc_type, exc, tb)
            self._bar = None
        elif self._target and self.current > 0 and not self.verbose:
            sys.stderr.write("\n")
            sys.stderr.flush()

    def step(self, item_hint: str | None = None, *, emit: bool = True) -> None:
        """Advance by one record and refresh the display."""
        self.current += 1
        if self._bar is not None:
            self._bar.update(1)
            return

        if not emit:
            return

        line = f"{self.prefix()} {self.label}"
        if item_hint:
            line += f" — {item_hint}"

        if self.verbose:
            click.secho(line, fg="white")
        elif self._target:
            sys.stderr.write(f"\r{line.ljust(96)}")
            sys.stderr.flush()

    def secho(self, message: str, **kwargs) -> None:
        """Verbose-aware ``click.secho`` with a progress prefix."""
        if self.verbose:
            click.secho(f"{self.prefix()} {message}", **kwargs)
        elif kwargs.get("fg") == "red":
            # Always show errors
            click.secho(message, **kwargs)

    def summary(self, *, dry_run: bool) -> str:
        """Final ``Processed X/Y`` fragment for completion messages."""
        if self._target is not None:
            return f"Processed {self.current:,}/{self._target:,}"
        return f"Processed {self.current:,}"
