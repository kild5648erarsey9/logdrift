"""Alerting module: triggers callbacks when log entry rates exceed thresholds."""

import time
import threading
from collections import deque
from typing import Callable, Deque, Dict, List, Optional


class RateAlert:
    """Fires an alert callback when entries exceed *max_count* within *window_seconds*."""

    def __init__(
        self,
        name: str,
        window_seconds: float,
        max_count: int,
        callback: Callable[[str, int, float], None],
        cooldown_seconds: float = 60.0,
    ) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_count < 1:
            raise ValueError("max_count must be >= 1")
        self.name = name
        self.window_seconds = window_seconds
        self.max_count = max_count
        self.callback = callback
        self.cooldown_seconds = cooldown_seconds
        self._timestamps: Deque[float] = deque()
        self._last_fired: Optional[float] = None
        self._lock = threading.Lock()

    def _evict_old(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def record(self, entry: Dict) -> bool:
        """Record an entry; returns True if the alert was fired."""
        now = time.time()
        with self._lock:
            self._evict_old(now)
            self._timestamps.append(now)
            count = len(self._timestamps)
            if count > self.max_count:
                if self._last_fired is None or (now - self._last_fired) >= self.cooldown_seconds:
                    self._last_fired = now
                    self.callback(self.name, count, self.window_seconds)
                    return True
        return False

    def current_count(self) -> int:
        """Return the number of entries recorded within the current window."""
        now = time.time()
        with self._lock:
            self._evict_old(now)
            return len(self._timestamps)


class AlertManager:
    """Manages a collection of RateAlert instances and routes entries to them."""

    def __init__(self) -> None:
        self._alerts: List[RateAlert] = []

    def register(self, alert: RateAlert) -> None:
        """Register an alert with the manager."""
        self._alerts.append(alert)

    def process(self, entry: Dict) -> None:
        """Forward *entry* to every registered alert."""
        for alert in self._alerts:
            alert.record(entry)

    @property
    def alerts(self) -> List[RateAlert]:
        return list(self._alerts)
