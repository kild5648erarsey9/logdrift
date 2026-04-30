"""Filter helpers for log entries produced by LogTailer."""

from typing import Callable, Iterable, List, Optional

LogEntry = dict
FilterFn = Callable[[LogEntry], bool]

LEVEL_ORDER = {
    "debug": 0,
    "info": 1,
    "warning": 2,
    "warn": 2,
    "error": 3,
    "critical": 4,
    "fatal": 4,
}


def by_level(min_level: str) -> FilterFn:
    """Return a filter that passes entries at or above *min_level*."""
    min_rank = LEVEL_ORDER.get(min_level.lower(), 0)

    def _filter(entry: LogEntry) -> bool:
        level = entry.get("level", "").lower()
        return LEVEL_ORDER.get(level, 0) >= min_rank

    return _filter


def by_service(services: List[str]) -> FilterFn:
    """Return a filter that passes entries whose service is in *services*."""
    allowed = {s.lower() for s in services}

    def _filter(entry: LogEntry) -> bool:
        return entry.get("service", "").lower() in allowed

    return _filter


def by_keyword(keyword: str) -> FilterFn:
    """Return a filter that passes entries whose message contains *keyword*."""
    kw = keyword.lower()

    def _filter(entry: LogEntry) -> bool:
        return kw in entry.get("message", "").lower()

    return _filter


def compose(*filters: FilterFn) -> FilterFn:
    """Combine multiple filters with AND semantics."""

    def _filter(entry: LogEntry) -> bool:
        return all(f(entry) for f in filters)

    return _filter


def apply_filters(
    entries: Iterable[LogEntry], filter_fn: Optional[FilterFn]
) -> Iterable[LogEntry]:
    """Lazily apply *filter_fn* to an iterable of log entries."""
    if filter_fn is None:
        return entries
    return (e for e in entries if filter_fn(e))
