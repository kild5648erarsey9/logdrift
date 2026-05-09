"""Aggregator that combines sampling, deduplication, and alerting in one pipeline."""

from typing import Callable, Dict, Iterable, Iterator, List, Optional

from logdrift.aggregator import LogAggregator
from logdrift.sampler import RateSampler
from logdrift.deduplicator import TimeWindowDeduplicator
from logdrift.alerting import AlertManager, RateAlert


class SamplingAlertingAggregator:
    """Wraps LogAggregator with optional sampling, deduplication, and alerting.

    Pipeline order for each entry:
        1. Deduplication  — drop exact duplicates within a time window
        2. Sampling       — probabilistically drop entries
        3. Alerting       — evaluate rate-based alert rules
        4. Yield          — pass the entry to the caller
    """

    def __init__(
        self,
        aggregator: LogAggregator,
        *,
        sample_rate: float = 1.0,
        dedup_window: Optional[float] = None,
        dedup_fields: Optional[List[str]] = None,
    ) -> None:
        self._aggregator = aggregator
        self._sampler = RateSampler(sample_rate)
        self._deduplicator: Optional[TimeWindowDeduplicator] = (
            TimeWindowDeduplicator(
                window_seconds=dedup_window,
                fields=dedup_fields or ["service", "level", "message"],
            )
            if dedup_window is not None
            else None
        )
        self._alert_manager = AlertManager()

    # ------------------------------------------------------------------
    # Alert registration
    # ------------------------------------------------------------------

    def add_alert(
        self,
        name: str,
        window_seconds: float,
        max_count: int,
        callback: Callable[[str, int, float], None],
        cooldown_seconds: float = 60.0,
    ) -> RateAlert:
        """Create, register, and return a new RateAlert."""
        alert = RateAlert(
            name,
            window_seconds=window_seconds,
            max_count=max_count,
            callback=callback,
            cooldown_seconds=cooldown_seconds,
        )
        self._alert_manager.register(alert)
        return alert

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def stream(self) -> Iterator[Dict]:
        """Yield log entries after applying the full pipeline."""
        for entry in self._aggregator.stream():
            if self._deduplicator and self._deduplicator.is_duplicate(entry):
                continue
            if not self._sampler.should_keep(entry):
                continue
            self._alert_manager.process(entry)
            yield entry
