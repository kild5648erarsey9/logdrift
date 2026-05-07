"""Aggregates log entries from multiple LogTailer instances into a single stream."""

import threading
import queue
from typing import Callable, Iterable, List, Optional

from logdrift.tailer import LogTailer


class LogAggregator:
    """Combines multiple LogTailer sources into one unified log stream."""

    def __init__(
        self,
        tailers: Iterable[LogTailer],
        filters: Optional[List[Callable[[dict], bool]]] = None,
        max_queue_size: int = 1000,
    ):
        self._tailers = list(tailers)
        self._filters = filters or []
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def _passes_filters(self, entry: dict) -> bool:
        return all(f(entry) for f in self._filters)

    def _tail_worker(self, tailer: LogTailer) -> None:
        for entry in tailer.tail():
            if self._stop_event.is_set():
                break
            if self._passes_filters(entry):
                try:
                    self._queue.put(entry, timeout=0.5)
                except queue.Full:
                    pass  # Drop entries when queue is full

    def start(self) -> None:
        """Start background threads for each tailer."""
        self._stop_event.clear()
        for tailer in self._tailers:
            t = threading.Thread(target=self._tail_worker, args=(tailer,), daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        """Signal all tailer threads to stop."""
        self._stop_event.set()

    def stream(self, timeout: float = 1.0):
        """Yield log entries from all sources as they arrive."""
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                entry = self._queue.get(timeout=timeout)
                yield entry
            except queue.Empty:
                continue

    def add_filter(self, f: Callable[[dict], bool]) -> None:
        """Attach an additional filter at runtime."""
        self._filters.append(f)
