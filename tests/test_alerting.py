"""Tests for logdrift.alerting."""

import time
import pytest
from unittest.mock import MagicMock
from logdrift.alerting import RateAlert, AlertManager


DUMMY_ENTRY = {"level": "ERROR", "service": "api", "message": "boom"}


# ---------------------------------------------------------------------------
# RateAlert
# ---------------------------------------------------------------------------

def test_rate_alert_no_fire_under_threshold():
    cb = MagicMock()
    alert = RateAlert("test", window_seconds=5.0, max_count=3, callback=cb)
    for _ in range(3):
        alert.record(DUMMY_ENTRY)
    cb.assert_not_called()


def test_rate_alert_fires_when_exceeded():
    cb = MagicMock()
    alert = RateAlert("test", window_seconds=5.0, max_count=2, callback=cb)
    for _ in range(3):
        alert.record(DUMMY_ENTRY)
    cb.assert_called_once()
    name, count, window = cb.call_args[0]
    assert name == "test"
    assert count == 3
    assert window == 5.0


def test_rate_alert_cooldown_prevents_double_fire():
    cb = MagicMock()
    alert = RateAlert("test", window_seconds=5.0, max_count=1, callback=cb, cooldown_seconds=60.0)
    for _ in range(5):
        alert.record(DUMMY_ENTRY)
    assert cb.call_count == 1


def test_rate_alert_fires_again_after_cooldown(monkeypatch):
    cb = MagicMock()
    alert = RateAlert("test", window_seconds=5.0, max_count=1, callback=cb, cooldown_seconds=10.0)
    alert.record(DUMMY_ENTRY)
    alert.record(DUMMY_ENTRY)  # fires
    assert cb.call_count == 1

    # Simulate time passing beyond cooldown
    monkeypatch.setattr(time, "time", lambda: time.time.__wrapped__() + 11)
    alert.record(DUMMY_ENTRY)  # should fire again
    assert cb.call_count == 2


def test_rate_alert_evicts_old_entries(monkeypatch):
    """Entries outside the window should not count."""
    cb = MagicMock()
    alert = RateAlert("test", window_seconds=2.0, max_count=2, callback=cb)
    # Manually inject old timestamps
    old = time.time() - 10
    alert._timestamps.extend([old, old])
    alert.record(DUMMY_ENTRY)  # only 1 entry in window — should not fire
    cb.assert_not_called()


def test_rate_alert_current_count():
    alert = RateAlert("test", window_seconds=5.0, max_count=100, callback=MagicMock())
    for _ in range(4):
        alert.record(DUMMY_ENTRY)
    assert alert.current_count() == 4


def test_rate_alert_invalid_window():
    with pytest.raises(ValueError, match="window_seconds"):
        RateAlert("x", window_seconds=0, max_count=1, callback=MagicMock())


def test_rate_alert_invalid_max_count():
    with pytest.raises(ValueError, match="max_count"):
        RateAlert("x", window_seconds=1.0, max_count=0, callback=MagicMock())


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------

def test_alert_manager_routes_to_all_alerts():
    cb1, cb2 = MagicMock(), MagicMock()
    mgr = AlertManager()
    mgr.register(RateAlert("a", 5.0, 1, cb1))
    mgr.register(RateAlert("b", 5.0, 1, cb2))
    mgr.process(DUMMY_ENTRY)
    mgr.process(DUMMY_ENTRY)
    cb1.assert_called_once()
    cb2.assert_called_once()


def test_alert_manager_alerts_property():
    mgr = AlertManager()
    a1 = RateAlert("a", 5.0, 10, MagicMock())
    a2 = RateAlert("b", 5.0, 10, MagicMock())
    mgr.register(a1)
    mgr.register(a2)
    assert mgr.alerts == [a1, a2]


def test_alert_manager_empty_no_error():
    mgr = AlertManager()
    mgr.process(DUMMY_ENTRY)  # should not raise
