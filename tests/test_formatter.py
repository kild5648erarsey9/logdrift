"""Tests for logdrift.formatter output formatting utilities."""

import json
import pytest

from logdrift.formatter import (
    format_text,
    format_json,
    format_compact,
    get_formatter,
    ANSI_COLORS,
)

SAMPLE_ENTRY = {
    "timestamp": "2024-03-15T10:22:05",
    "level": "ERROR",
    "service": "auth-service",
    "message": "Token validation failed",
    "request_id": "abc-123",
}


def test_format_text_contains_key_fields():
    result = format_text(SAMPLE_ENTRY, colorize=False)
    assert "2024-03-15" in result
    assert "ERROR" in result
    assert "auth-service" in result
    assert "Token validation failed" in result


def test_format_text_colorize_adds_ansi():
    result = format_text(SAMPLE_ENTRY, colorize=True)
    assert ANSI_COLORS["ERROR"] in result
    assert ANSI_COLORS["RESET"] in result


def test_format_text_no_color_no_ansi():
    result = format_text(SAMPLE_ENTRY, colorize=False)
    assert "\033[" not in result


def test_format_text_custom_timestamp_fmt():
    result = format_text(SAMPLE_ENTRY, colorize=False, timestamp_fmt="%d/%m/%Y")
    assert "15/03/2024" in result


def test_format_text_missing_timestamp_graceful():
    entry = {"level": "INFO", "service": "svc", "message": "ok"}
    result = format_text(entry, colorize=False)
    assert "INFO" in result
    assert "ok" in result


def test_format_json_is_valid_json():
    result = format_json(SAMPLE_ENTRY)
    parsed = json.loads(result)
    assert parsed["level"] == "ERROR"
    assert parsed["request_id"] == "abc-123"


def test_format_json_indent():
    result = format_json(SAMPLE_ENTRY, indent=2)
    assert "\n" in result


def test_format_compact_contains_all_fields():
    result = format_compact(SAMPLE_ENTRY)
    assert "timestamp=" in result
    assert "level=" in result
    assert "service=" in result
    assert "message=" in result
    assert "request_id=" in result


def test_format_compact_no_missing_keys():
    entry = {"level": "DEBUG", "message": "ping"}
    result = format_compact(entry)
    assert "level='DEBUG'" in result
    assert "message='ping'" in result


def test_get_formatter_text():
    fmt = get_formatter("text")
    assert callable(fmt)
    assert "ERROR" in fmt(SAMPLE_ENTRY, colorize=False)


def test_get_formatter_json():
    fmt = get_formatter("json")
    parsed = json.loads(fmt(SAMPLE_ENTRY))
    assert parsed["service"] == "auth-service"


def test_get_formatter_compact():
    fmt = get_formatter("compact")
    assert "level=" in fmt(SAMPLE_ENTRY)


def test_get_formatter_unknown_raises():
    with pytest.raises(ValueError, match="Unknown format"):
        get_formatter("xml")
