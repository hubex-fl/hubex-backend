"""Shared test infrastructure for HUBEX backend tests.

Provides reusable helpers for in-memory SQLite sessions, JWT token generation,
and FastAPI test app construction. Existing tests that define their own helpers
still work — these are opt-in utilities for new or refactored tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.db.base import Base


# ---------------------------------------------------------------------------
# In-memory SQLite session factory
# ---------------------------------------------------------------------------

async def make_test_session(
    tables: Sequence[Any] | None = None,
    extra_ddl: list[str] | None = None,
):
    """Create an in-memory SQLite engine + session factory.

    Args:
        tables: SQLAlchemy Table objects to create via metadata.create_all.
                 If None, creates ALL tables from Base.metadata.
        extra_ddl: Raw SQL statements to run after table creation (e.g. for
                   minimal stub tables that avoid complex FK chains).

    Returns:
        (engine, SessionFactory) tuple.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def _create(conn):
        if tables:
            Base.metadata.create_all(conn, tables=list(tables))
        else:
            Base.metadata.create_all(conn)
        for ddl in extra_ddl or []:
            conn.execute(text(ddl))

    async with engine.begin() as conn:
        await conn.run_sync(_create)

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, Session


# ---------------------------------------------------------------------------
# JWT token helper
# ---------------------------------------------------------------------------

def make_token(
    sub: str = "1",
    caps: list[str] | None = None,
    expire_seconds: int = 600,
    **extra_claims: Any,
) -> str:
    """Generate a JWT token for test requests."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iss": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + expire_seconds,
        "caps": caps or [],
        **extra_claims,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def auth_header(sub: str = "1", caps: list[str] | None = None) -> dict[str, str]:
    """Shortcut: returns {"Authorization": "Bearer <token>"}."""
    return {"Authorization": f"Bearer {make_token(sub=sub, caps=caps)}"}


# ---------------------------------------------------------------------------
# FastAPI test app builder
# ---------------------------------------------------------------------------

async def make_test_app(
    Session,
    routers: list | None = None,
    prefix: str = "/api/v1",
    with_cap_guard: bool = True,
):
    """Build a minimal FastAPI app wired to a test session.

    Args:
        Session: async_sessionmaker from make_test_session.
        routers: List of APIRouter instances to include.
        prefix: URL prefix for all routers.
        with_cap_guard: If True, attach capability_guard as a dependency.

    Returns:
        FastAPI app instance.
    """
    async def _get_test_db():
        async with Session() as s:
            yield s

    deps = [Depends(capability_guard)] if with_cap_guard else []
    app = FastAPI(dependencies=deps)
    app.dependency_overrides[get_db] = _get_test_db

    for router in routers or []:
        app.include_router(router, prefix=prefix)

    return app


def make_client(app: FastAPI) -> httpx.AsyncClient:
    """Create an httpx.AsyncClient for the given FastAPI app."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")
