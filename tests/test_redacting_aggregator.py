"""Tests for logdrift.redacting_aggregator."""

from __future__ import annotations

from queue import Queue
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock, patch

import pytest

from logdrift.redactor import Redactor, _REDACTED
from logdrift.redacting_aggregator import RedactingAggregator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_aggregator(entries: List[Dict[str, Any]]) -> MagicMock:
    """Return a mock LogAggregator whose stream() yields *entries*."""
    agg = MagicMock()
    agg.stream.return_value = iter(entries)
    return agg


def _collect(ra: RedactingAggregator, **kwargs: Any) -> List[Dict[str, Any]]:
    return list(ra.stream(**kwargs))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_stream_redacts_sensitive_fields():
    entries = [
        {"level": "INFO", "msg": "login", "password": "s3cr3t"},
        {"level": "DEBUG", "msg": "ok", "password": "abc"},
    ]
    agg = _make_mock_aggregator(entries)
    ra = RedactingAggregator(agg, Redactor(fields=["password"]))

    results = _collect(ra)
    assert all(r["password"] == _REDACTED for r in results)
    assert results[0]["msg"] == "login"


def test_stream_passes_through_without_redactor():
    entries = [{"level": "INFO", "msg": "hello"}]
    agg = _make_mock_aggregator(entries)
    ra = RedactingAggregator(agg)  # no redactor → noop

    results = _collect(ra)
    assert results == entries


def test_stream_applies_pattern_redaction():
    entries = [{"msg": "token=abc123 used", "svc": "auth"}]
    agg = _make_mock_aggregator(entries)
    ra = RedactingAggregator(agg, Redactor(patterns=[r"token=[A-Za-z0-9]+"]))

    results = _collect(ra)
    assert results[0]["msg"] == _REDACTED
    assert results[0]["svc"] == "auth"


def test_start_and_stop_delegated():
    agg = _make_mock_aggregator([])
    ra = RedactingAggregator(agg)
    ra.start()
    ra.stop()
    agg.start.assert_called_once()
    agg.stop.assert_called_once()


def test_context_manager_calls_start_stop():
    agg = _make_mock_aggregator([])
    with RedactingAggregator(agg) as ra:
        pass
    agg.start.assert_called_once()
    agg.stop.assert_called_once()


def test_stream_empty_source_yields_nothing():
    agg = _make_mock_aggregator([])
    ra = RedactingAggregator(agg, Redactor(fields=["secret"]))
    assert _collect(ra) == []


def test_stream_timeout_forwarded_to_aggregator():
    agg = _make_mock_aggregator([])
    ra = RedactingAggregator(agg)
    _collect(ra, timeout=0.5)
    agg.stream.assert_called_once_with(timeout=0.5)
