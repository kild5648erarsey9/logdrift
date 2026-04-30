"""Tests for logdrift.tailer and logdrift.filters."""

import json
import os
import tempfile
import threading
import time

import pytest

from logdrift.filters import (
    apply_filters,
    by_keyword,
    by_level,
    by_service,
    compose,
)
from logdrift.tailer import LogTailer


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------

def test_by_level_passes_equal_or_above():
    f = by_level("warning")
    assert f({"level": "warning", "message": "x"}) is True
    assert f({"level": "error", "message": "x"}) is True
    assert f({"level": "info", "message": "x"}) is False


def test_by_service_case_insensitive():
    f = by_service(["Auth", "gateway"])
    assert f({"service": "auth"}) is True
    assert f({"service": "GATEWAY"}) is True
    assert f({"service": "worker"}) is False


def test_by_keyword():
    f = by_keyword("timeout")
    assert f({"message": "Connection timeout reached"}) is True
    assert f({"message": "all good"}) is False


def test_compose_all_must_pass():
    f = compose(by_level("error"), by_keyword("disk"))
    assert f({"level": "error", "message": "disk full"}) is True
    assert f({"level": "error", "message": "memory low"}) is False
    assert f({"level": "info", "message": "disk full"}) is False


def test_apply_filters_none_passes_all():
    entries = [{"level": "debug"}, {"level": "info"}]
    result = list(apply_filters(entries, None))
    assert result == entries


# ---------------------------------------------------------------------------
# Tailer tests
# ---------------------------------------------------------------------------

def _write_lines(path: str, lines: list, delay: float = 0.05) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for line in lines:
            time.sleep(delay)
            f.write(line + "\n")
            f.flush()


def test_tailer_parses_json_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tailer = LogTailer(tmp_path, service_name="svc", seek_end=False)
        entries_json = [
            json.dumps({"level": "info", "message": "started"}),
            json.dumps({"level": "error", "message": "boom"}),
        ]
        with open(tmp_path, "w") as f:
            for line in entries_json:
                f.write(line + "\n")

        collected = []
        gen = tailer.tail()
        for _ in range(2):
            collected.append(next(gen))

        assert collected[0]["message"] == "started"
        assert collected[1]["level"] == "error"
        assert all(e["service"] == "svc" for e in collected)
    finally:
        os.unlink(tmp_path)


def test_tailer_handles_non_json_line():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with open(tmp_path, "w") as f:
            f.write("plain text log line\n")

        tailer = LogTailer(tmp_path, service_name="svc", seek_end=False)
        entry = next(tailer.tail())
        assert entry["message"] == "plain text log line"
        assert entry["service"] == "svc"
    finally:
        os.unlink(tmp_path)
