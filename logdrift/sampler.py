"""Rate-based and reservoir sampling for high-volume log streams."""

import random
import threading
from typing import Any, Dict, List, Optional


class RateSampler:
    """Pass through approximately *rate* fraction of log entries (0.0–1.0)."""

    def __init__(self, rate: float = 1.0, seed: Optional[int] = None) -> None:
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"rate must be between 0.0 and 1.0, got {rate}")
        self.rate = rate
        self._rng = random.Random(seed)

    def should_keep(self, entry: Dict[str, Any]) -> bool:  # noqa: ARG002
        """Return True if the entry should be kept."""
        return self.rate >= 1.0 or self._rng.random() < self.rate


class ReservoirSampler:
    """Maintain a fixed-size reservoir sample (Algorithm R) over a stream.

    Call :meth:`add` for every entry; retrieve the current reservoir via
    :attr:`reservoir`.  Thread-safe.
    """

    def __init__(self, capacity: int = 100, seed: Optional[int] = None) -> None:
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self.capacity = capacity
        self._rng = random.Random(seed)
        self._reservoir: List[Dict[str, Any]] = []
        self._count = 0
        self._lock = threading.Lock()

    def add(self, entry: Dict[str, Any]) -> bool:
        """Add *entry* to the reservoir.  Returns True if the entry was kept."""
        with self._lock:
            self._count += 1
            if len(self._reservoir) < self.capacity:
                self._reservoir.append(entry)
                return True
            idx = self._rng.randint(0, self._count - 1)
            if idx < self.capacity:
                self._reservoir[idx] = entry
                return True
            return False

    @property
    def reservoir(self) -> List[Dict[str, Any]]:
        """Return a snapshot of the current reservoir."""
        with self._lock:
            return list(self._reservoir)

    @property
    def total_seen(self) -> int:
        with self._lock:
            return self._count

    def reset(self) -> None:
        with self._lock:
            self._reservoir.clear()
            self._count = 0
