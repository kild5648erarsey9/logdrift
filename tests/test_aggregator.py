"""Tests for LogAggregator."""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from logdrift.aggregator import LogAggregator


def _make_tailer(entries):
    """Return a mock LogTailer whose tail() yields the given entries."""
    tailer = MagicMock()
    tailer.tail.return_value = iter(entries)
    return tailer


SAMPLE_ENTRIES = [
    {"level": "INFO", "service": "api", "message": "started"},
    {"level": "ERROR", "service": "db", "message": "connection lost"},
    {"level": "DEBUG", "service": "api", "message": "query ok"},
]


def _collect(aggregator, count, timeout=2.0):
    """Collect up to *count* entries from aggregator.stream()."""
    results = []
    deadline = time.time() + timeout
    for entry in aggregator.stream(timeout=0.1):
        results.append(entry)
        if len(results) >= count or time.time() > deadline:
            break
    aggregator.stop()
    return results


def test_aggregator_yields_all_entries_from_single_tailer():
    tailer = _make_tailer(SAMPLE_ENTRIES)
    agg = LogAggregator([tailer])
    agg.start()
    results = _collect(agg, len(SAMPLE_ENTRIES))
    assert len(results) == len(SAMPLE_ENTRIES)


def test_aggregator_merges_multiple_tailers():
    t1 = _make_tailer(SAMPLE_ENTRIES[:2])
    t2 = _make_tailer(SAMPLE_ENTRIES[2:])
    agg = LogAggregator([t1, t2])
    agg.start()
    results = _collect(agg, 3)
    assert len(results) == 3


def test_aggregator_applies_filters():
    only_error = lambda e: e.get("level") == "ERROR"
    tailer = _make_tailer(SAMPLE_ENTRIES)
    agg = LogAggregator([tailer], filters=[only_error])
    agg.start()
    results = _collect(agg, 1)
    assert all(e["level"] == "ERROR" for e in results)


def test_aggregator_add_filter_at_runtime():
    tailer = _make_tailer(SAMPLE_ENTRIES)
    agg = LogAggregator([tailer])
    agg.add_filter(lambda e: e.get("service") == "api")
    agg.start()
    results = _collect(agg, 2)
    assert all(e["service"] == "api" for e in results)


def test_aggregator_stop_ends_stream():
    import queue as q_mod

    tailer = _make_tailer([])  # no entries
    agg = LogAggregator([tailer])
    agg.start()
    agg.stop()
    results = list(agg.stream(timeout=0.05))
    assert results == []


def test_aggregator_no_filters_passes_all():
    tailer = _make_tailer(SAMPLE_ENTRIES)
    agg = LogAggregator([tailer])
    agg.start()
    results = _collect(agg, len(SAMPLE_ENTRIES))
    assert len(results) == len(SAMPLE_ENTRIES)
