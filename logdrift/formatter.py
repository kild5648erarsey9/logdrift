"""Output formatting utilities for logdrift log entries."""

import json
from datetime import datetime
from typing import Any, Dict, Optional

ANSI_COLORS = {
    "DEBUG": "\033[36m",    # Cyan
    "INFO": "\033[32m",     # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",    # Red
    "CRITICAL": "\033[35m", # Magenta
    "RESET": "\033[0m",
}


def _colorize(level: str, text: str) -> str:
    color = ANSI_COLORS.get(level.upper(), "")
    reset = ANSI_COLORS["RESET"]
    return f"{color}{text}{reset}" if color else text


def format_text(
    entry: Dict[str, Any],
    colorize: bool = True,
    timestamp_fmt: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """Format a log entry as a human-readable text line."""
    ts_raw = entry.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts_raw).strftime(timestamp_fmt)
    except (ValueError, TypeError):
        ts = ts_raw or "?"

    level = entry.get("level", "INFO").upper()
    service = entry.get("service", "unknown")
    message = entry.get("message", "")

    level_str = f"[{level:<8}]"
    if colorize:
        level_str = _colorize(level, level_str)

    return f"{ts}  {level_str}  {service:<20}  {message}"


def format_json(entry: Dict[str, Any], indent: Optional[int] = None) -> str:
    """Format a log entry as a JSON string."""
    return json.dumps(entry, default=str, indent=indent)


def format_compact(entry: Dict[str, Any]) -> str:
    """Format a log entry as a minimal key=value line."""
    parts = []
    for key in ("timestamp", "level", "service", "message"):
        value = entry.get(key)
        if value is not None:
            parts.append(f"{key}={value!r}")
    extras = {k: v for k, v in entry.items() if k not in {"timestamp", "level", "service", "message"}}
    for k, v in extras.items():
        parts.append(f"{k}={v!r}")
    return " ".join(parts)


FORMATS = {
    "text": format_text,
    "json": format_json,
    "compact": format_compact,
}


def get_formatter(fmt: str):
    """Return a formatter callable by name. Raises ValueError for unknown formats."""
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format {fmt!r}. Choose from: {list(FORMATS)}.")
    return FORMATS[fmt]
