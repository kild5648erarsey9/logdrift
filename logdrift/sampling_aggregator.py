"""Aggregator variant that integrates rate and reservoir sampling."""

from typing import Any, Dict, Iterable, Iterator, List, Optional

from logdrift.aggregator import LogAggregator
from logdrift.sampler import RateSampler, ReservoirSampler
from logdrift.tailer import LogTailer


class SamplingAggregator(LogAggregator):
    """Extends :class:`LogAggregator` with optional rate and reservoir sampling.

    Parameters
    ----------
    tailers:
        One or more :class:`LogTailer` instances to aggregate.
    filters:
        Optional filter callables (same contract as :mod:`logdrift.filters`).
    rate:
        Fraction of entries to forward downstream (1.0 = all).
    reservoir_capacity:
        If > 0, a :class:`ReservoirSampler` is maintained in parallel so
        callers can retrieve a statistical sample via :attr:`reservoir`.
    seed:
        Optional RNG seed for reproducible sampling.
    """

    def __init__(
        self,
        tailers: List[LogTailer],
        filters: Optional[List[Any]] = None,
        *,
        rate: float = 1.0,
        reservoir_capacity: int = 0,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(tailers, filters=filters)
        self._rate_sampler = RateSampler(rate=rate, seed=seed)
        self._reservoir: Optional[ReservoirSampler] = (
            ReservoirSampler(capacity=reservoir_capacity, seed=seed)
            if reservoir_capacity > 0
            else None
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def reservoir(self) -> List[Dict[str, Any]]:
        """Current reservoir snapshot, or empty list if not configured."""
        if self._reservoir is None:
            return []
        return self._reservoir.reservoir

    # ------------------------------------------------------------------
    # Override the generator to inject sampling
    # ------------------------------------------------------------------

    def stream(self) -> Iterator[Dict[str, Any]]:
        """Yield sampled entries from the aggregated stream."""
        for entry in super().stream():
            if self._reservoir is not None:
                self._reservoir.add(entry)
            if self._rate_sampler.should_keep(entry):
                yield entry
