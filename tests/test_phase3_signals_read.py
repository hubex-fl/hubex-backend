from __future__ import annotations
from datetime import datetime, timezone

import pytest
import httpx
from fastapi import Depends, FastAPI
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.signals import router as signals_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.security import ALGORITHM, ISSUER, SECRET_KEY
from app.core.signals import MAX_LIMIT, read_signals
from app.db.base import Base
from app.db.models.providers import ProviderInstance, ProviderType
from app.db.models.signals import SignalV1


def _create_phase3_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            ProviderType.__table__,
            ProviderInstance.__table__,
            SignalV1.__table__,
        ],
    )


@pytest.mark.asyncio
async def test_read_signals_pagination_deterministic_and_monotonic():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_phase3_tables(Base.metadata, c))

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        db.add_all(
            [
                SignalV1(
                    id=1,
                    stream="tenant.system",
                    signal_type="t",
                    payload={"i": 1},
                    idempotency_key="k1",
                    provider_instance_id=None,
                ),
                SignalV1(
                    id=2,
                    stream="other",
                    signal_type="t",
                    payload={"i": 99},
                    idempotency_key="ko",
                    provider_instance_id=None,
                ),
                SignalV1(
                    id=3,
                    stream="tenant.system",
                    signal_type="t",
                    payload={"i": 2},
                    idempotency_key="k2",
                    provider_instance_id=None,
                ),
                SignalV1(
                    id=4,
                    stream="tenant.system",
                    signal_type="t",
                    payload={"i": 3},
                    idempotency_key="k3",
                    provider_instance_id=None,
                ),
            ]
        )
        await db.commit()

        seen: list[int] = []
        cursor: int | None = None
        while True:
            items, next_cursor = await read_signals(db, stream="tenant.system", cursor=cursor, limit=2)
            ids = [it.id for it in items]
            assert ids == sorted(ids)
            assert not (set(ids) & set(seen))
            seen.extend(ids)
            if next_cursor is None:
                break
            assert cursor is None or next_cursor > cursor
            cursor = next_cursor

        assert len(seen) == 3
        assert seen == sorted(seen)


@pytest.mark.asyncio
async def test_read_signals_limit_is_clamped():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_phase3_tables(Base.metadata, c))

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        for i in range(MAX_LIMIT + 5):
            db.add(
                SignalV1(
                    id=i + 1,
                    stream="tenant.system",
                    signal_type="t",
                    payload={"i": i},
                    idempotency_key=f"kc{i}",
                    provider_instance_id=None,
                )
            )
        await db.commit()

        items, next_cursor = await read_signals(db, stream="tenant.system", cursor=0, limit=MAX_LIMIT + 1000)
        assert len(items) == MAX_LIMIT
        assert next_cursor is not None


@pytest.mark.asyncio
async def test_signals_endpoint_capability_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    # Other tests mutate CAPABILITY_MAP; ensure this route is mapped.
    CAPABILITY_MAP[("GET", "/api/v1/signals")] = ["signals.read"]

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_phase3_tables(Base.metadata, c))

    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with Session() as db:
        db.add(
            SignalV1(
                id=1,
                stream="tenant.system",
                signal_type="t",
                payload={"i": 1},
                idempotency_key="k1",
                provider_instance_id=None,
            )
        )
        await db.commit()

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(signals_router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")

    # No token => 401
    res = await client.get("/api/v1/signals", params={"stream": "tenant.system"})
    assert res.status_code == 401

    now = datetime.now(timezone.utc)
    token_no_cap = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": ["devices.read"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    res = await client.get(
        "/api/v1/signals",
        params={"stream": "tenant.system"},
        headers={"Authorization": f"Bearer {token_no_cap}"},
    )
    assert res.status_code == 403

    token_ok = jwt.encode(
        {
            "sub": "1",
            "iss": ISSUER,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 600,
            "caps": ["signals.read"],
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    res = await client.get(
        "/api/v1/signals",
        params={"stream": "tenant.system", "limit": 10},
        headers={"Authorization": f"Bearer {token_ok}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "next_cursor" in body

    await client.aclose()
