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
from app.api.v1.audit import router as audit_router
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


def _token(sub: str, caps: list[str]) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": sub,
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": caps,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


@pytest.mark.asyncio
async def test_module_enabled_guard_and_audit(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/audit")] = ["audit.read"]
    CAPABILITY_MAP[("GET", "/api/v1/modules")] = ["modules.read"]
    CAPABILITY_MAP[("POST", "/api/v1/modules/{key}/enable")] = ["modules.write"]
    CAPABILITY_MAP[("POST", "/api/v1/modules/{key}/disable")] = ["modules.write"]

    engine, Session = await _mk_session()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(modules_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    module_token = _token("module:rules_min", ["audit.read"])
    user_token = _token("1", ["modules.write", "modules.read", "audit.read"])

    blocked = await client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {module_token}"},
    )
    assert blocked.status_code == 403
    assert blocked.json().get("code") == "MODULE_DISABLED"

    enabled = await client.post(
        "/api/v1/modules/rules_min/enable",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True

    allowed = await client.get(
        "/api/v1/audit",
        headers={"Authorization": f"Bearer {module_token}"},
    )
    assert allowed.status_code == 200

    disabled = await client.post(
        "/api/v1/modules/rules_min/disable",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    async with Session() as db:
        res = await db.execute(
            AuditV1Entry.__table__.select().order_by(AuditV1Entry.id.asc())
        )
        rows = res.fetchall()
        actions = [row.action for row in rows]
        assert "module.enable" in actions
        assert "module.disable" in actions

    await client.aclose()
    await engine.dispose()
