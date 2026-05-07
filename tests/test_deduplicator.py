"""Tests for logdrift.deduplicator."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from logdrift.deduplicator import (
    CountWindowDeduplicator,
    TimeWindowDeduplicator,
    _entry_fingerprint,
)

_ENTRY = {"level": "ERROR", "service": "api", "message": "timeout"}


# ---------------------------------------------------------------------------
# _entry_fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_same_fields_same_digest():
    assert _entry_fingerprint(_ENTRY, ("level", "message")) == \
           _entry_fingerprint(_ENTRY, ("level", "message"))


def test_fingerprint_different_values_differ():
    other = {**_ENTRY, "message": "connection refused"}
    assert _entry_fingerprint(_ENTRY, ("message",)) != \
           _entry_fingerprint(other, ("message",))


def test_fingerprint_missing_field_treated_as_empty():
    a = _entry_fingerprint({"level": "INFO"}, ("level", "service"))
    b = _entry_fingerprint({"level": "INFO", "service": ""}, ("level", "service"))
    assert a == b


# ---------------------------------------------------------------------------
# TimeWindowDeduplicator
# ---------------------------------------------------------------------------

def test_time_window_first_occurrence_not_duplicate():
    d = TimeWindowDeduplicator(window_seconds=10)
    assert d.is_duplicate(_ENTRY) is False


def test_time_window_second_occurrence_is_duplicate():
    d = TimeWindowDeduplicator(window_seconds=10)
    d.is_duplicate(_ENTRY)
    assert d.is_duplicate(_ENTRY) is True


def test_time_window_different_entries_not_duplicate():
    d = TimeWindowDeduplicator(window_seconds=10)
    d.is_duplicate(_ENTRY)
    other = {**_ENTRY, "message": "disk full"}
    assert d.is_duplicate(other) is False


def test_time_window_expired_entry_not_duplicate():
    d = TimeWindowDeduplicator(window_seconds=1)
    # First call at t=0
    with patch("logdrift.deduplicator.time.monotonic", return_value=0.0):
        d.is_duplicate(_ENTRY)
    # Second call after window expires
    with patch("logdrift.deduplicator.time.monotonic", return_value=2.0):
        assert d.is_duplicate(_ENTRY) is False


def test_time_window_reset_clears_cache():
    d = TimeWindowDeduplicator(window_seconds=60)
    d.is_duplicate(_ENTRY)
    d.reset()
    assert d.is_duplicate(_ENTRY) is False


def test_time_window_max_cache_evicts_oldest():
    d = TimeWindowDeduplicator(window_seconds=60, max_cache=3)
    entries = [{"message": str(i)} for i in range(3)]
    for e in entries:
        d.is_duplicate(e)
    assert len(d._cache) == 3
    # Adding a 4th should evict the oldest
    d.is_duplicate({"message": "new"})
    assert len(d._cache) == 3


def test_time_window_invalid_window_raises():
    with pytest.raises(ValueError):
        TimeWindowDeduplicator(window_seconds=0)


# ---------------------------------------------------------------------------
# CountWindowDeduplicator
# ---------------------------------------------------------------------------

def test_count_window_first_occurrence_not_duplicate():
    d = CountWindowDeduplicator(max_count=1)
    assert d.is_duplicate(_ENTRY) is False


def test_count_window_second_occurrence_is_duplicate():
    d = CountWindowDeduplicator(max_count=1)
    d.is_duplicate(_ENTRY)
    assert d.is_duplicate(_ENTRY) is True


def test_count_window_max_count_two_allows_twice():
    d = CountWindowDeduplicator(max_count=2)
    assert d.is_duplicate(_ENTRY) is False
    assert d.is_duplicate(_ENTRY) is False
    assert d.is_duplicate(_ENTRY) is True


def test_count_window_reset_clears_counts():
    d = CountWindowDeduplicator(max_count=1)
    d.is_duplicate(_ENTRY)
    d.reset()
    assert d.is_duplicate(_ENTRY) is False


def test_count_window_invalid_max_count_raises():
    with pytest.raises(ValueError):
        CountWindowDeduplicator(max_count=0)
