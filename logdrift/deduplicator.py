"""Deduplication support for log entries.

Provides a sliding-window deduplicator that suppresses repeated log
entries within a configurable time window, and a count-based variant
useful for tests or non-time-sensitive pipelines.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Any, Dict, Optional


def _entry_fingerprint(entry: Dict[str, Any], fields: tuple[str, ...]) -> str:
    """Return a stable hex digest for the subset of *fields* in *entry*."""
    parts = "|".join(str(entry.get(f, "")) for f in sorted(fields))
    return hashlib.md5(parts.encode(), usedforsecurity=False).hexdigest()


class TimeWindowDeduplicator:
    """Suppress duplicate log entries seen within *window_seconds*.

    Two entries are considered duplicates when they share identical
    values for every field listed in *key_fields*.

    Parameters
    ----------
    window_seconds:
        How long (in seconds) a fingerprint is remembered.
    key_fields:
        Entry fields that together form the dedup key.  Defaults to
        ``("level", "service", "message")``.
    max_cache:
        Upper bound on the number of fingerprints kept in memory.
    """

    def __init__(
        self,
        window_seconds: float = 60.0,
        key_fields: tuple[str, ...] = ("level", "service", "message"),
        max_cache: int = 4096,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.window_seconds = window_seconds
        self.key_fields = key_fields
        self.max_cache = max_cache
        # fingerprint -> expiry timestamp
        self._cache: OrderedDict[str, float] = OrderedDict()

    def _evict_expired(self, now: float) -> None:
        expired = [fp for fp, exp in self._cache.items() if exp <= now]
        for fp in expired:
            del self._cache[fp]

    def is_duplicate(self, entry: Dict[str, Any]) -> bool:
        """Return *True* if *entry* is a duplicate and should be suppressed."""
        now = time.monotonic()
        self._evict_expired(now)
        fp = _entry_fingerprint(entry, self.key_fields)
        if fp in self._cache:
            return True
        # Evict oldest entry when cache is full
        if len(self._cache) >= self.max_cache:
            self._cache.popitem(last=False)
        self._cache[fp] = now + self.window_seconds
        return False

    def reset(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()


class CountWindowDeduplicator:
    """Suppress a duplicate after it has been seen *max_count* times.

    Unlike :class:`TimeWindowDeduplicator` this variant is deterministic
    and does not depend on wall-clock time, making it convenient for
    testing and count-based pipelines.
    """

    def __init__(
        self,
        max_count: int = 1,
        key_fields: tuple[str, ...] = ("level", "service", "message"),
    ) -> None:
        if max_count < 1:
            raise ValueError("max_count must be >= 1")
        self.max_count = max_count
        self.key_fields = key_fields
        self._counts: Dict[str, int] = {}

    def is_duplicate(self, entry: Dict[str, Any]) -> bool:
        """Return *True* once the entry has been seen more than *max_count* times."""
        fp = _entry_fingerprint(entry, self.key_fields)
        count = self._counts.get(fp, 0) + 1
        self._counts[fp] = count
        return count > self.max_count

    def reset(self) -> None:
        """Reset all counters."""
        self._counts.clear()
