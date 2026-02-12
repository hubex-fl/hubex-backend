from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.capabilities import CAPABILITY_REGISTRY
from app.core.signals import persist_signal
from app.db.models.signals import SignalV1


class _FakeAsyncSession:
    def __init__(self) -> None:
        self._rows: list[SignalV1] = []
        self._pending: SignalV1 | None = None
        self._next_id = 1

    async def scalar(self, stmt):
        params = stmt.compile().params
        stream = params.get("stream_1")
        idem = params.get("idempotency_key_1")
        for row in self._rows:
            if row.stream == stream and row.idempotency_key == idem:
                return row
        return None

    def add(self, signal: SignalV1) -> None:
        self._pending = signal

    async def commit(self) -> None:
        if self._pending is None:
            return
        for row in self._rows:
            if (
                row.stream == self._pending.stream
                and row.idempotency_key == self._pending.idempotency_key
            ):
                raise IntegrityError("duplicate idempotency key", params=None, orig=None)
        self._pending.id = self._next_id
        self._next_id += 1
        self._rows.append(self._pending)
        self._pending = None

    async def refresh(self, signal: SignalV1) -> None:
        _ = signal

    async def rollback(self) -> None:
        self._pending = None


@pytest.mark.asyncio
async def test_persist_signal_dedupes_idempotency_key():
    db = _FakeAsyncSession()

    first = await persist_signal(
        db,
        stream="tenant.system",
        signal_type="device.ping",
        payload={"n": 1},
        idempotency_key="idem-1",
    )
    second = await persist_signal(
        db,
        stream="tenant.system",
        signal_type="device.ping",
        payload={"n": 1},
        idempotency_key="idem-1",
    )

    assert first.created is True
    assert second.created is False
    assert first.cursor == second.cursor
    assert len(db._rows) == 1


@pytest.mark.asyncio
async def test_persist_signal_allows_same_idempotency_key_across_streams():
    db = _FakeAsyncSession()

    a = await persist_signal(
        db,
        stream="tenant.system",
        signal_type="device.ping",
        payload={"n": 1},
        idempotency_key="idem-1",
    )
    b = await persist_signal(
        db,
        stream="tenant.other",
        signal_type="device.ping",
        payload={"n": 1},
        idempotency_key="idem-1",
    )

    assert a.created is True
    assert b.created is True
    assert a.cursor != b.cursor
    assert len(db._rows) == 2


@pytest.mark.asyncio
async def test_persist_signal_cursor_is_monotonic():
    db = _FakeAsyncSession()

    one = await persist_signal(
        db,
        stream="tenant.system",
        signal_type="device.ping",
        payload={"n": 1},
        idempotency_key="idem-1",
    )
    two = await persist_signal(
        db,
        stream="tenant.system",
        signal_type="device.ping",
        payload={"n": 2},
        idempotency_key="idem-2",
    )
    three = await persist_signal(
        db,
        stream="tenant.system",
        signal_type="device.ping",
        payload={"n": 3},
        idempotency_key="idem-3",
    )

    assert one.created and two.created and three.created
    assert one.cursor < two.cursor < three.cursor
    assert [row.id for row in db._rows] == [one.cursor, two.cursor, three.cursor]


def test_signals_ingest_capability_placeholder_present():
    assert "signals.ingest" in CAPABILITY_REGISTRY
