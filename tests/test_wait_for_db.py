from __future__ import annotations

import pytest

from app.scripts.wait_for_db import wait_for_db


@pytest.mark.asyncio
async def test_wait_for_db_times_out_fast():
    ok = await wait_for_db(
        "postgresql+asyncpg://user:pass@127.0.0.1:1/db",
        timeout_seconds=0.2,
        interval_seconds=0.05,
    )
    assert ok is False
