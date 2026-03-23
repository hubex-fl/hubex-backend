"""Security-hardening middleware bundle.

Applies in a single pass:
  - X-Request-ID header (UUID, echoed from client or freshly generated)
  - Security headers (X-Content-Type-Options, X-Frame-Options, HSTS, etc.)
  - X-API-Version: v1 header
  - Access log (method, path, status, duration_ms)
  - Max request body size (default 1 MB) — rejects oversized bodies with 413
  - Max URL length (default 2048 chars) — rejects with 414
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.logging_config import set_request_context, clear_request_context

logger = logging.getLogger("hubex.access")

_MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB
_MAX_URL_LENGTH = 2048

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-API-Version": "v1",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    """Applies security headers, request-ID, access log, and input limits."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # --- URL length guard ---
        if len(str(request.url)) > _MAX_URL_LENGTH:
            return JSONResponse(
                status_code=414,
                content={"detail": "request_uri_too_long"},
            )

        # --- Body size guard (via Content-Length header) ---
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "request_entity_too_large"},
            )

        # --- Request-ID ---
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

        # --- Set logging context ---
        set_request_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            clear_request_context()

        duration_ms = int((time.perf_counter() - start) * 1000)

        # --- Access log ---
        logger.info(
            "access",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        # --- Add headers to response ---
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        response.headers["X-Request-ID"] = request_id

        return response
