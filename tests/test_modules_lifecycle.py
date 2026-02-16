from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.modules import router as modules_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.db.base import Base
from app.db.models.audit import AuditV1Entry
from app.db.models.modules import ModuleRegistry


def _create_tables(metadata, conn) -> None:
    metadata.create_all(conn, tables=[ModuleRegistry.__table__, AuditV1Entry.__table__])


async def _mk_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_tables(Base.metadata, c))
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, Session


def _token(caps: list[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": caps,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


@pytest.mark.asyncio
async def test_modules_read_caps_and_list(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/modules")] = ["modules.read"]
    CAPABILITY_MAP[("GET", "/api/v1/modules/{key}")] = ["modules.read"]

    engine, Session = await _mk_session()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(modules_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    res = await client.get("/api/v1/modules")
    assert res.status_code == 401

    bad = await client.get(
        "/api/v1/modules",
        headers={"Authorization": f"Bearer {_token(['devices.read'])}"},
    )
    assert bad.status_code == 403

    ok = await client.get(
        "/api/v1/modules",
        headers={"Authorization": f"Bearer {_token(['modules.read'])}"},
    )
    assert ok.status_code == 200
    items = ok.json()
    keys = [m["key"] for m in items]
    assert "rules_min" in keys
    rules = next(m for m in items if m["key"] == "rules_min")
    assert rules["enabled"] is False

    detail = await client.get(
        "/api/v1/modules/rules_min",
        headers={"Authorization": f"Bearer {_token(['modules.read'])}"},
    )
    assert detail.status_code == 200
    assert detail.json()["key"] == "rules_min"

    await client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_modules_enable_disable(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/modules")] = ["modules.read"]
    CAPABILITY_MAP[("GET", "/api/v1/modules/{key}")] = ["modules.read"]
    CAPABILITY_MAP[("POST", "/api/v1/modules/{key}/enable")] = ["modules.write"]
    CAPABILITY_MAP[("POST", "/api/v1/modules/{key}/disable")] = ["modules.write"]

    engine, Session = await _mk_session()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(modules_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    write_headers = {"Authorization": f"Bearer {_token(['modules.write'])}"}
    read_headers = {"Authorization": f"Bearer {_token(['modules.read'])}"}

    enabled = await client.post("/api/v1/modules/rules_min/enable", headers=write_headers)
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    detail = await client.get("/api/v1/modules/rules_min", headers=read_headers)
    assert detail.status_code == 200
    assert detail.json()["enabled"] is True

    disabled = await client.post("/api/v1/modules/rules_min/disable", headers=write_headers)
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    await client.aclose()
    await engine.dispose()
