"""Structured logging configuration for HUBEX backend.

When log_format == "json" (HUBEX_LOG_FORMAT=json), every log record is emitted
as a JSON object that includes:
  timestamp, level, name, message, request_id, user_id, org_id, path, method

Request-scoped fields (request_id, path, method) are injected via a ContextVar
that middleware populates at the start of each request.

Structured logging is intentionally NOT activated in test environments
(HUBEX_ENV=test or pytest) to avoid noisy JSON output in test output.
"""
from __future__ import annotations

import contextvars
import logging
import os
import sys
from typing import Any

_ctx: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "hubex_log_ctx", default={}
)


def set_request_context(**kwargs: Any) -> None:
    _ctx.set(dict(kwargs))


def clear_request_context() -> None:
    _ctx.set({})


def get_request_context() -> dict[str, Any]:
    return _ctx.get()


# ---------------------------------------------------------------------------
# Custom log filter that merges request context into each record
# ---------------------------------------------------------------------------

class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        ctx = _ctx.get()
        for key, val in ctx.items():
            if not hasattr(record, key):
                setattr(record, key, val)
        # Ensure fields always present (even outside a request)
        for field in ("request_id", "path", "method", "user_id", "org_id"):
            if not hasattr(record, field):
                setattr(record, field, None)
        return True


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def configure_logging(log_level: str = "INFO", log_format: str = "text") -> None:
    """Configure logging. Must NOT be called in test environments."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    ctx_filter = _ContextFilter()

    if log_format == "json":
        try:
            from pythonjsonlogger import jsonlogger

            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s "
                    "%(request_id)s %(path)s %(method)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
                rename_fields={"asctime": "timestamp", "levelname": "level"},
            )
        except ImportError:
            logging.basicConfig(level=level)
            return
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(ctx_filter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def is_test_env() -> bool:
    """Return True when running under pytest or HUBEX_ENV=test."""
    return (
        os.getenv("HUBEX_ENV", "").lower() == "test"
        or "pytest" in sys.modules
    )
