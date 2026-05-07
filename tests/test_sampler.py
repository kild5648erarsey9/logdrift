"""Tests for logdrift.sampler and logdrift.sampling_aggregator."""

import pytest

from logdrift.sampler import RateSampler, ReservoirSampler
from logdrift.sampling_aggregator import SamplingAggregator


# ---------------------------------------------------------------------------
# RateSampler
# ---------------------------------------------------------------------------

def test_rate_sampler_keeps_all_at_1():
    s = RateSampler(rate=1.0, seed=0)
    entries = [{"msg": str(i)} for i in range(50)]
    assert all(s.should_keep(e) for e in entries)


def test_rate_sampler_drops_all_at_0():
    s = RateSampler(rate=0.0, seed=0)
    entries = [{"msg": str(i)} for i in range(50)]
    assert not any(s.should_keep(e) for e in entries)


def test_rate_sampler_approximate_half(seed=42):
    s = RateSampler(rate=0.5, seed=seed)
    kept = sum(1 for _ in range(1000) if s.should_keep({}))
    assert 400 < kept < 600, f"expected ~500 kept, got {kept}"


def test_rate_sampler_invalid_rate():
    with pytest.raises(ValueError):
        RateSampler(rate=1.5)
    with pytest.raises(ValueError):
        RateSampler(rate=-0.1)


# ---------------------------------------------------------------------------
# ReservoirSampler
# ---------------------------------------------------------------------------

def test_reservoir_fills_up_to_capacity():
    r = ReservoirSampler(capacity=10, seed=0)
    for i in range(10):
        r.add({"i": i})
    assert len(r.reservoir) == 10
    assert r.total_seen == 10


def test_reservoir_does_not_exceed_capacity():
    r = ReservoirSampler(capacity=5, seed=0)
    for i in range(200):
        r.add({"i": i})
    assert len(r.reservoir) == 5
    assert r.total_seen == 200


def test_reservoir_reset_clears_state():
    r = ReservoirSampler(capacity=5, seed=0)
    for i in range(20):
        r.add({"i": i})
    r.reset()
    assert r.reservoir == []
    assert r.total_seen == 0


def test_reservoir_invalid_capacity():
    with pytest.raises(ValueError):
        ReservoirSampler(capacity=0)


# ---------------------------------------------------------------------------
# SamplingAggregator
# ---------------------------------------------------------------------------

class _FakeTailer:
    """Minimal stand-in for LogTailer."""

    def __init__(self, entries):
        self._entries = entries
        self.path = "fake.log"

    def tail(self):
        yield from self._entries


def _make_entries(n=20):
    return [{"level": "INFO", "service": "svc", "msg": str(i)} for i in range(n)]


def test_sampling_aggregator_rate_1_passes_all():
    tailer = _FakeTailer(_make_entries(20))
    agg = SamplingAggregator([tailer], rate=1.0, seed=0)
    results = list(agg.stream())
    assert len(results) == 20


def test_sampling_aggregator_rate_0_drops_all():
    tailer = _FakeTailer(_make_entries(20))
    agg = SamplingAggregator([tailer], rate=0.0, seed=0)
    results = list(agg.stream())
    assert results == []


def test_sampling_aggregator_reservoir_populated():
    entries = _make_entries(50)
    tailer = _FakeTailer(entries)
    agg = SamplingAggregator([tailer], rate=1.0, reservoir_capacity=10, seed=0)
    list(agg.stream())  # consume fully
    assert len(agg.reservoir) == 10


def test_sampling_aggregator_no_reservoir_returns_empty():
    tailer = _FakeTailer(_make_entries(10))
    agg = SamplingAggregator([tailer], rate=1.0)
    list(agg.stream())
    assert agg.reservoir == []
