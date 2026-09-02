"""Shared output helpers for session-kit scripts.

All formatters output JSON-compatible data.
"""

from __future__ import annotations

import calendar
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        dt = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def to_json(obj: Any) -> str:
    """Compact JSON serialization. Handles datetime and set."""
    return json.dumps(obj, default=_json_default, separators=(",", ":"))


def to_ndjson(items: list) -> str:
    """Newline-delimited JSON for streaming results."""
    if not items:
        return ""
    return "\n".join(to_json(item) for item in items) + "\n"


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis if over max_len."""
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}..."


def format_duration(total_seconds: float) -> str:
    """Human-readable duration from seconds."""
    seconds = int(total_seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m" if secs == 0 else f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h" if mins == 0 else f"{hours}h {mins}m"


def format_size(num_bytes: int) -> str:
    """Human-readable file size."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def parse_timestamp(ts: str | int | float | None) -> datetime | None:
    """Parse a timestamp from session JSONL. Handles epoch ms, epoch s, ISO strings."""
    if ts is None:
        return None
    try:
        if isinstance(ts, (int, float)):
            seconds = ts / 1000 if ts > 1e12 else ts
            return datetime.fromtimestamp(seconds, tz=UTC)
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def render_table(rows: list[dict], columns: list[dict]) -> str:
    """
    Format a list of dicts as a plain-text aligned table.
    columns: list of {"key", "label", "align": "left"|"right", "width": int, "format": callable}
    """
    cells: list[list[str]] = []
    for row in rows:
        row_cells = []
        for col in columns:
            raw = row.get(col["key"])
            fmt: Callable[[Any], str] | None = col.get("format")
            val = fmt(raw) if fmt else str(raw if raw is not None else "")
            width = col.get("width")
            if width and len(val) > width:
                val = truncate(val, max(width - 3, 0))
            row_cells.append(val)
        cells.append(row_cells)

    widths = [
        max(len(col["label"]), max((len(row[i]) for row in cells), default=0))
        for i, col in enumerate(columns)
    ]

    def pad(text: str, width: int, align: str) -> str:
        return text.rjust(width) if align == "right" else text.ljust(width)

    header = "  ".join(
        pad(col["label"], widths[i], col.get("align", "left")) for i, col in enumerate(columns)
    )
    # Plain ASCII rather than box-drawing characters: Windows' default console
    # codepage (cp1252) can't encode U+2500 and crashes stdout on print().
    sep = "--".join("-" * w for w in widths)
    data_lines = [
        "  ".join(
            pad(row[i], widths[i], columns[i].get("align", "left")) for i in range(len(columns))
        )
        for row in cells
    ]
    footer = f"{len(rows)} row{'' if len(rows) == 1 else 's'}"

    return "\n".join([header, sep, *data_lines, footer])


_REL_PATTERN = re.compile(r"^(\d+)([dwm])$")


def _subtract_months(dt: datetime, months: int) -> datetime:
    total = dt.month - 1 - months
    year = dt.year + total // 12
    month = total % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def parse_date_boundary(input_str: str | None) -> datetime | None:
    """
    Parse a date range boundary string.
    Accepts: ISO date ("2026-04-01"), relative shorthand ("7d", "2w", "3m"),
    or ISO datetime ("2026-04-01T14:00:00Z").
    Returns a datetime or None if unparseable.
    """
    if not input_str:
        return None

    rel_match = _REL_PATTERN.match(input_str)
    if rel_match:
        n = int(rel_match.group(1))
        unit = rel_match.group(2)
        now = datetime.now(UTC)
        if unit == "d":
            return now - timedelta(days=n)
        if unit == "w":
            return now - timedelta(weeks=n)
        return _subtract_months(now, n)

    try:
        dt = datetime.fromisoformat(input_str.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except ValueError:
        return None
