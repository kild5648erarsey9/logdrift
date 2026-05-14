"""
logdrift.redactor
~~~~~~~~~~~~~~~~~
Sensitive-field redaction for structured log entries.

Supports exact-key redaction and regex-pattern redaction on string values.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Pattern

_REDACTED = "***REDACTED***"


def _redact_value(value: Any, patterns: List[Pattern[str]]) -> Any:
    """Return a redacted copy of *value* if it matches any pattern."""
    if not isinstance(value, str):
        return value
    for pat in patterns:
        if pat.search(value):
            return _REDACTED
    return value


def make_field_redactor(fields: Iterable[str]) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Return a function that blanks out exact field names in a log entry dict."""
    blocked: frozenset[str] = frozenset(f.lower() for f in fields)

    def _redact(entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: (_REDACTED if k.lower() in blocked else v)
            for k, v in entry.items()
        }

    return _redact


def make_pattern_redactor(
    patterns: Iterable[str],
    flags: int = re.IGNORECASE,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Return a function that redacts string values matching any regex pattern."""
    compiled: List[Pattern[str]] = [re.compile(p, flags) for p in patterns]

    def _redact(entry: Dict[str, Any]) -> Dict[str, Any]:
        return {k: _redact_value(v, compiled) for k, v in entry.items()}

    return _redact


class Redactor:
    """Combines field-name and value-pattern redaction into a single callable."""

    def __init__(
        self,
        fields: Optional[Iterable[str]] = None,
        patterns: Optional[Iterable[str]] = None,
    ) -> None:
        self._steps: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []
        if fields:
            self._steps.append(make_field_redactor(fields))
        if patterns:
            self._steps.append(make_pattern_redactor(patterns))

    def redact(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all redaction steps to *entry* and return the sanitised copy."""
        for step in self._steps:
            entry = step(entry)
        return entry

    def __call__(self, entry: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        return self.redact(entry)
