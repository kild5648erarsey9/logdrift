"""Tests for logdrift.redactor."""

import pytest

from logdrift.redactor import (
    Redactor,
    _REDACTED,
    make_field_redactor,
    make_pattern_redactor,
)


# ---------------------------------------------------------------------------
# make_field_redactor
# ---------------------------------------------------------------------------

def test_field_redactor_removes_listed_fields():
    fn = make_field_redactor(["password", "token"])
    entry = {"user": "alice", "password": "s3cr3t", "token": "abc123"}
    result = fn(entry)
    assert result["password"] == _REDACTED
    assert result["token"] == _REDACTED
    assert result["user"] == "alice"


def test_field_redactor_case_insensitive():
    fn = make_field_redactor(["Password"])
    result = fn({"PASSWORD": "hunter2"})
    assert result["PASSWORD"] == _REDACTED


def test_field_redactor_leaves_unlisted_fields_intact():
    fn = make_field_redactor(["secret"])
    entry = {"message": "hello", "level": "INFO"}
    assert fn(entry) == entry


def test_field_redactor_non_string_value_redacted():
    fn = make_field_redactor(["pin"])
    result = fn({"pin": 1234})
    assert result["pin"] == _REDACTED


# ---------------------------------------------------------------------------
# make_pattern_redactor
# ---------------------------------------------------------------------------

def test_pattern_redactor_matches_credit_card():
    fn = make_pattern_redactor([r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"])
    result = fn({"msg": "card: 4111 1111 1111 1111", "level": "INFO"})
    assert result["msg"] == _REDACTED
    assert result["level"] == "INFO"


def test_pattern_redactor_no_match_unchanged():
    fn = make_pattern_redactor([r"secret"])
    entry = {"msg": "nothing sensitive here"}
    assert fn(entry) == entry


def test_pattern_redactor_skips_non_string_values():
    fn = make_pattern_redactor([r"\d+"])
    result = fn({"count": 42, "label": "abc"})
    assert result["count"] == 42  # not a string, left alone


# ---------------------------------------------------------------------------
# Redactor class
# ---------------------------------------------------------------------------

def test_redactor_combines_field_and_pattern():
    r = Redactor(fields=["api_key"], patterns=[r"\bpassword=\S+"])
    entry = {
        "api_key": "key-xyz",
        "msg": "password=hunter2 logged in",
        "level": "DEBUG",
    }
    out = r.redact(entry)
    assert out["api_key"] == _REDACTED
    assert out["msg"] == _REDACTED
    assert out["level"] == "DEBUG"


def test_redactor_empty_config_is_noop():
    r = Redactor()
    entry = {"msg": "hello", "level": "INFO"}
    assert r.redact(entry) == entry


def test_redactor_only_fields():
    r = Redactor(fields=["ssn"])
    result = r.redact({"ssn": "123-45-6789", "name": "Bob"})
    assert result["ssn"] == _REDACTED
    assert result["name"] == "Bob"


def test_redactor_only_patterns():
    r = Redactor(patterns=[r"\btoken=[A-Za-z0-9]+"])
    result = r.redact({"msg": "auth token=abc123 ok", "svc": "auth"})
    assert result["msg"] == _REDACTED
    assert result["svc"] == "auth"


def test_redactor_does_not_mutate_original():
    r = Redactor(fields=["secret"])
    original = {"secret": "shh", "msg": "hi"}
    _ = r.redact(original)
    assert original["secret"] == "shh"  # original untouched
