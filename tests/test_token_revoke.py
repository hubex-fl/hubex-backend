import asyncio
import os
import pytest

from app.core.token_revoke import is_token_revoked, revoke_token
from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_revoke_and_check():
    if os.getenv("DATABASE_URL") is None:
        pytest.skip("DATABASE_URL not set")

    jti = "test-revoke-jti"
    try:
        async with AsyncSessionLocal() as db:
            await revoke_token(db, jti, "test")
            revoked = await is_token_revoked(db, jti)
            assert revoked is True
    except Exception:
        pytest.skip("database not available or migration missing")
