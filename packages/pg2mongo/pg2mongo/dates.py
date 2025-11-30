from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

import click


def parse_user_date(value: str) -> datetime:
    """
    Accepts:
      - YYYY-MM-DD
      - MM-DD-YYYY
    Returns timezone-aware UTC datetime at midnight.
    """
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m-%d-%Y"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise click.BadParameter(f"Invalid date format: {value}")


def inclusive_window(
    start_str: str, end_str: str | None
) -> Tuple[str, str]:
    """
    Given user start/end strings, return ISO-like strings suitable
    for Postgres queries.
    """
    start_dt = parse_user_date(start_str)

    if end_str:
        end_dt = parse_user_date(end_str).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    else:
        now = datetime.now(timezone.utc)
        end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_iso = start_dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    end_iso = end_dt.strftime("%Y-%m-%d %H:%M:%S.%f%z")
    return start_iso, end_iso
