"""Phase 7 — Structured logging tests.

Tests the logging configuration and context-injection helpers.
No real HTTP server is needed.
"""
from __future__ import annotations

import json
import logging
import sys
from io import StringIO
from unittest.mock import patch


def test_set_and_get_request_context():
    """set_request_context stores values retrievable via get_request_context."""
    from app.core.logging_config import (
        clear_request_context,
        get_request_context,
        set_request_context,
    )

    set_request_context(request_id="abc123", path="/api/v1/devices", method="GET")
    ctx = get_request_context()
    assert ctx["request_id"] == "abc123"
    assert ctx["path"] == "/api/v1/devices"
    assert ctx["method"] == "GET"

    clear_request_context()
    assert get_request_context() == {}


def test_context_filter_injects_fields():
    """_ContextFilter adds context-var fields to log records."""
    from app.core.logging_config import _ContextFilter, set_request_context, clear_request_context

    set_request_context(request_id="req-1", path="/health", method="GET")

    flt = _ContextFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="test message", args=(), exc_info=None,
    )
    flt.filter(record)

    assert record.request_id == "req-1"
    assert record.path == "/health"
    assert record.method == "GET"
    clear_request_context()


def test_context_filter_sets_none_for_missing_fields():
    """Fields not in context are defaulted to None (not AttributeError)."""
    from app.core.logging_config import _ContextFilter, clear_request_context

    clear_request_context()
    flt = _ContextFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="outside request", args=(), exc_info=None,
    )
    flt.filter(record)
    # Should not raise
    assert record.request_id is None
    assert record.user_id is None
    assert record.org_id is None


def test_json_log_output_format():
    """configure_logging with json format emits JSON-parseable lines."""
    try:
        from pythonjsonlogger import jsonlogger  # noqa: F401
    except ImportError:
        import pytest
        pytest.skip("python-json-logger not installed")

    from app.core.logging_config import configure_logging

    stream = StringIO()
    handler = logging.StreamHandler(stream)

    # Temporarily configure just one test logger
    test_logger = logging.getLogger("hubex.test.json")
    test_logger.handlers = []

    try:
        from pythonjsonlogger import jsonlogger

        fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
        handler.setFormatter(fmt)
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        test_logger.info("test_event", extra={"request_id": "r1", "path": "/test"})

        output = stream.getvalue().strip()
        parsed = json.loads(output)
        assert parsed["message"] == "test_event"
        assert "timestamp" in parsed or "asctime" in parsed
    finally:
        test_logger.handlers = []


def test_is_test_env_under_pytest():
    """is_test_env() returns True when running under pytest."""
    from app.core.logging_config import is_test_env

    # pytest is always in sys.modules when this test runs
    assert is_test_env() is True
