"""
logdrift.redacting_aggregator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Aggregator wrapper that applies a Redactor to every log entry before
yielding it downstream.  Composes cleanly with SamplingAlertingAggregator.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, Iterable, Optional

from logdrift.aggregator import LogAggregator
from logdrift.redactor import Redactor


class RedactingAggregator:
    """
    Wraps a :class:`~logdrift.aggregator.LogAggregator` and passes every
    emitted entry through a :class:`~logdrift.redactor.Redactor` before
    yielding it to the caller.

    Parameters
    ----------
    aggregator:
        An already-configured ``LogAggregator`` instance.
    redactor:
        A ``Redactor`` instance.  If *None*, a no-op redactor is created.
    """

    def __init__(
        self,
        aggregator: LogAggregator,
        redactor: Optional[Redactor] = None,
    ) -> None:
        self._aggregator = aggregator
        self._redactor = redactor if redactor is not None else Redactor()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the underlying aggregator's background threads."""
        self._aggregator.start()

    def stop(self) -> None:
        """Stop the underlying aggregator."""
        self._aggregator.stop()

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def stream(
        self, timeout: float = 0.1
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield redacted log entries from the underlying aggregator."""
        for entry in self._aggregator.stream(timeout=timeout):
            yield self._redactor.redact(entry)

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "RedactingAggregator":
        self.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop()
