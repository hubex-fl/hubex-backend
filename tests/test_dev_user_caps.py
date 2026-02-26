from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import verify_password
from app.db.base import Base
from app.db.models.user import User
from app.scripts.seed_dev_user_caps import (
    DEFAULT_EMAIL,
    DEFAULT_PASSWORD,
    _all_caps,
    ensure_dev_user_caps_db,
)


def _create_tables(metadata, conn) -> None:
    metadata.create_all(conn, tables=[User.__table__])


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


@pytest.mark.asyncio
async def test_seed_dev_user_caps_includes_reissue():
    engine, Session = await _mk_session()
    async with Session() as db:
        user, updated = await ensure_dev_user_caps_db(
            db,
            email=DEFAULT_EMAIL,
            password=DEFAULT_PASSWORD,
            caps=_all_caps(),
            force_password=True,
        )
        assert user.email == DEFAULT_EMAIL
        assert "devices.token.reissue" in (user.caps or [])
        assert "devices.unclaim" in (user.caps or [])
        assert "telemetry.read" in (user.caps or [])
        assert "pairing.claim" in (user.caps or [])
        assert updated
        assert verify_password(DEFAULT_PASSWORD, user.password_hash)

    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_dev_user_caps_merges_default_with_override():
    override = ["users.read", "events.read"]
    engine, Session = await _mk_session()
    async with Session() as db:
        user, _ = await ensure_dev_user_caps_db(
            db,
            email=DEFAULT_EMAIL,
            password=DEFAULT_PASSWORD,
            caps=_all_caps(override),
            force_password=True,
        )
        assert "devices.token.reissue" in (user.caps or [])
        assert "devices.unclaim" in (user.caps or [])
        assert "users.read" in (user.caps or [])
        assert "events.read" in (user.caps or [])
        assert "pairing.claim" in (user.caps or [])

    await engine.dispose()
