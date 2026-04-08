"""Tests for Alert Rules CRUD, Alert Events API, alert worker, and metrics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.alerts import router as alerts_router
from app.api.v1.metrics import router as metrics_router
from app.core.alert_worker import run_alert_cycle
from app.core.capabilities import CAPABILITY_MAP
from app.db.base import Base
from app.db.models.alerts import AlertEvent, AlertRule
from app.db.models.device import Device
from app.db.models.effects import EffectV1
from app.db.models.entities import Entity, EntityDeviceBinding
from app.db.models.events import EventV1
from app.db.models.webhooks import WebhookSubscription
from tests.conftest import make_token


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            AlertRule.__table__,
            AlertEvent.__table__,
            Device.__table__,
            Entity.__table__,
            EntityDeviceBinding.__table__,
            EffectV1.__table__,
            EventV1.__table__,
            WebhookSubscription.__table__,
        ],
    )


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


async def _mk_app(Session, routers=None):
    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    for r in (routers or [alerts_router]):
        app.include_router(r, prefix="/api/v1")
    return app


def _auth(caps: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(caps=caps)}"}


# ---------------------------------------------------------------------------
# Capability map coverage
# ---------------------------------------------------------------------------

def test_capability_map_has_alerts_entries():
    assert ("POST", "/api/v1/alerts/rules") in CAPABILITY_MAP
    assert ("GET", "/api/v1/alerts") in CAPABILITY_MAP
    assert ("POST", "/api/v1/alerts/{event_id}/ack") in CAPABILITY_MAP
    assert ("GET", "/api/v1/metrics") in CAPABILITY_MAP


# ---------------------------------------------------------------------------
# Alert Rules CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_alert_rule():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Offline Rule",
                "condition_type": "device_offline",
                "condition_config": {"threshold_seconds": 120},
                "severity": "warning",
            },
            headers=_auth(["alerts.write"]),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Offline Rule"
    assert data["condition_type"] == "device_offline"
    assert data["enabled"] is True
    assert data["cooldown_seconds"] == 300


@pytest.mark.asyncio
async def test_create_alert_rule_invalid_condition_type():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/alerts/rules",
            json={"name": "Bad", "condition_type": "nonexistent", "condition_config": {}},
            headers=_auth(["alerts.write"]),
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_alert_rules():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        await c.post(
            "/api/v1/alerts/rules",
            json={"name": "R1", "condition_type": "event_lag", "condition_config": {"stream": "system", "max_lag_seconds": 60}},
            headers=_auth(["alerts.write"]),
        )
        await c.post(
            "/api/v1/alerts/rules",
            json={"name": "R2", "condition_type": "device_offline", "condition_config": {}, "enabled": False},
            headers=_auth(["alerts.write"]),
        )
        resp_all = await c.get("/api/v1/alerts/rules", headers=_auth(["alerts.read"]))
        resp_enabled = await c.get("/api/v1/alerts/rules?enabled=true", headers=_auth(["alerts.read"]))
        resp_disabled = await c.get("/api/v1/alerts/rules?enabled=false", headers=_auth(["alerts.read"]))

    assert len(resp_all.json()) == 2
    assert len(resp_enabled.json()) == 1
    assert len(resp_disabled.json()) == 1


@pytest.mark.asyncio
async def test_get_alert_rule_not_found():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/alerts/rules/999", headers=_auth(["alerts.read"]))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_alert_rule():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        create = await c.post(
            "/api/v1/alerts/rules",
            json={"name": "Old Name", "condition_type": "device_offline", "condition_config": {}},
            headers=_auth(["alerts.write"]),
        )
        rule_id = create.json()["id"]
        resp = await c.put(
            f"/api/v1/alerts/rules/{rule_id}",
            json={"name": "New Name", "severity": "critical", "enabled": False},
            headers=_auth(["alerts.write"]),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["severity"] == "critical"
    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_delete_alert_rule():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        create = await c.post(
            "/api/v1/alerts/rules",
            json={"name": "ToDelete", "condition_type": "device_offline", "condition_config": {}},
            headers=_auth(["alerts.write"]),
        )
        rule_id = create.json()["id"]
        del_resp = await c.delete(f"/api/v1/alerts/rules/{rule_id}", headers=_auth(["alerts.write"]))
        get_resp = await c.get(f"/api/v1/alerts/rules/{rule_id}", headers=_auth(["alerts.read"]))

    assert del_resp.status_code == 204
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Alert Events API
# ---------------------------------------------------------------------------

async def _seed_rule(Session, condition_type="device_offline") -> int:
    async with Session() as db:
        rule = AlertRule(
            name="test-rule",
            condition_type=condition_type,
            condition_config={},
            severity="warning",
            enabled=True,
            cooldown_seconds=300,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule.id


async def _seed_event(Session, rule_id: int, status: str = "firing") -> int:
    async with Session() as db:
        ev = AlertEvent(
            rule_id=rule_id,
            status=status,
            message="test alert",
            triggered_at=datetime.now(timezone.utc),
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        return ev.id


@pytest.mark.asyncio
async def test_list_alert_events_empty():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/alerts", headers=_auth(["alerts.read"]))

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_alert_events_filter_by_status():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    rule_id = await _seed_rule(Session)
    await _seed_event(Session, rule_id, "firing")
    await _seed_event(Session, rule_id, "resolved")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp_all = await c.get("/api/v1/alerts", headers=_auth(["alerts.read"]))
        resp_firing = await c.get("/api/v1/alerts?status=firing", headers=_auth(["alerts.read"]))
        resp_resolved = await c.get("/api/v1/alerts?status=resolved", headers=_auth(["alerts.read"]))

    assert len(resp_all.json()) == 2
    assert len(resp_firing.json()) == 1
    assert len(resp_resolved.json()) == 1


@pytest.mark.asyncio
async def test_get_alert_event_not_found():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/alerts/999", headers=_auth(["alerts.read"]))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_acknowledge_alert_event():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    rule_id = await _seed_rule(Session)
    event_id = await _seed_event(Session, rule_id, "firing")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/alerts/{event_id}/ack",
            json={"acknowledged_by": "admin"},
            headers=_auth(["alerts.write"]),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_by"] == "admin"
    assert data["acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_acknowledge_already_acknowledged_is_idempotent():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    rule_id = await _seed_rule(Session)
    event_id = await _seed_event(Session, rule_id, "acknowledged")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/alerts/{event_id}/ack",
            json={},
            headers=_auth(["alerts.write"]),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_acknowledge_resolved_returns_409():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    rule_id = await _seed_rule(Session)
    event_id = await _seed_event(Session, rule_id, "resolved")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/alerts/{event_id}/ack",
            json={},
            headers=_auth(["alerts.write"]),
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_resolve_alert_event():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    rule_id = await _seed_rule(Session)
    event_id = await _seed_event(Session, rule_id, "acknowledged")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/alerts/{event_id}/resolve",
            headers=_auth(["alerts.write"]),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


@pytest.mark.asyncio
async def test_resolve_already_resolved_is_idempotent():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    rule_id = await _seed_rule(Session)
    event_id = await _seed_event(Session, rule_id, "resolved")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/alerts/{event_id}/resolve",
            headers=_auth(["alerts.write"]),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


# ---------------------------------------------------------------------------
# Alert worker — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_fires_device_offline_alert():
    _, Session = await _mk_session()
    now = datetime.now(timezone.utc)

    async with Session() as db:
        # Device last seen 3 minutes ago (> 120s threshold)
        device = Device(
            device_uid="dev-offline",
            is_claimed=True,
            last_seen_at=now - timedelta(seconds=200),
        )
        db.add(device)
        rule = AlertRule(
            name="offline-rule",
            condition_type="device_offline",
            condition_config={"threshold_seconds": 120},
            severity="warning",
            enabled=True,
            cooldown_seconds=300,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        await db.commit()

    async with Session() as db:
        await run_alert_cycle(db, now)

    async with Session() as db:
        from sqlalchemy import select
        res = await db.execute(select(AlertEvent))
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].status == "firing"
    assert "offline" in events[0].message.lower()


@pytest.mark.asyncio
async def test_worker_no_alert_when_device_online():
    _, Session = await _mk_session()
    now = datetime.now(timezone.utc)

    async with Session() as db:
        device = Device(
            device_uid="dev-online",
            is_claimed=True,
            last_seen_at=now - timedelta(seconds=5),
        )
        db.add(device)
        rule = AlertRule(
            name="offline-rule",
            condition_type="device_offline",
            condition_config={"threshold_seconds": 120},
            severity="warning",
            enabled=True,
            cooldown_seconds=300,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        await db.commit()

    async with Session() as db:
        await run_alert_cycle(db, now)

    async with Session() as db:
        from sqlalchemy import select
        res = await db.execute(select(AlertEvent))
        events = list(res.scalars().all())

    assert len(events) == 0


@pytest.mark.asyncio
async def test_worker_respects_cooldown():
    _, Session = await _mk_session()
    now = datetime.now(timezone.utc)

    async with Session() as db:
        device = Device(
            device_uid="dev-offline-cd",
            is_claimed=True,
            last_seen_at=now - timedelta(seconds=200),
        )
        db.add(device)
        rule = AlertRule(
            name="offline-rule",
            condition_type="device_offline",
            condition_config={"threshold_seconds": 120},
            severity="warning",
            enabled=True,
            cooldown_seconds=600,  # 10 min cooldown
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        rule_id = rule.id

    # First cycle — should fire
    async with Session() as db:
        await run_alert_cycle(db, now)

    from sqlalchemy import select

    async with Session() as db:
        res = await db.execute(select(AlertEvent).where(AlertEvent.rule_id == rule_id))
        events_after_first = list(res.scalars().all())

    assert len(events_after_first) == 1

    # Manually resolve the event so condition is still true but cooldown applies
    async with Session() as db:
        res = await db.execute(select(AlertEvent).where(AlertEvent.rule_id == rule_id))
        ev = res.scalar_one()
        ev.status = "resolved"
        ev.resolved_at = now
        await db.commit()

    # Second cycle immediately after — should NOT fire again (within cooldown)
    async with Session() as db:
        await run_alert_cycle(db, now + timedelta(seconds=1))

    async with Session() as db:
        res = await db.execute(select(AlertEvent).where(AlertEvent.rule_id == rule_id))
        events_after_second = list(res.scalars().all())

    assert len(events_after_second) == 1  # no new event


@pytest.mark.asyncio
async def test_worker_auto_resolves_when_condition_clears():
    _, Session = await _mk_session()
    now = datetime.now(timezone.utc)

    async with Session() as db:
        device = Device(
            device_uid="dev-recover",
            is_claimed=True,
            last_seen_at=now - timedelta(seconds=200),
        )
        db.add(device)
        rule = AlertRule(
            name="offline-rule",
            condition_type="device_offline",
            condition_config={"threshold_seconds": 120},
            severity="warning",
            enabled=True,
            cooldown_seconds=0,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(device)
        await db.refresh(rule)
        rule_id = rule.id
        device_id = device.id

    # First cycle — fires
    async with Session() as db:
        await run_alert_cycle(db, now)

    from sqlalchemy import select

    # Device comes back online
    async with Session() as db:
        res = await db.execute(select(Device).where(Device.id == device_id))
        dev = res.scalar_one()
        dev.last_seen_at = now + timedelta(seconds=5)
        await db.commit()

    # Second cycle — condition is false, should auto-resolve
    async with Session() as db:
        await run_alert_cycle(db, now + timedelta(seconds=10))

    async with Session() as db:
        res = await db.execute(select(AlertEvent).where(AlertEvent.rule_id == rule_id))
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].status == "resolved"
    assert events[0].resolved_at is not None


@pytest.mark.asyncio
async def test_worker_event_lag_condition():
    _, Session = await _mk_session()
    now = datetime.now(timezone.utc)

    async with Session() as db:
        # Insert an event that is too old
        old_event = EventV1(
            stream="telemetry",
            ts=now - timedelta(seconds=400),
            type="telemetry.received",
            payload={},
        )
        db.add(old_event)
        rule = AlertRule(
            name="lag-rule",
            condition_type="event_lag",
            condition_config={"stream": "telemetry", "max_lag_seconds": 300},
            severity="info",
            enabled=True,
            cooldown_seconds=0,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        await db.commit()

    async with Session() as db:
        await run_alert_cycle(db, now)

    from sqlalchemy import select
    async with Session() as db:
        res = await db.execute(select(AlertEvent))
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].status == "firing"


@pytest.mark.asyncio
async def test_worker_disabled_rule_skipped():
    _, Session = await _mk_session()
    now = datetime.now(timezone.utc)

    async with Session() as db:
        device = Device(
            device_uid="dev-dis",
            is_claimed=True,
            last_seen_at=now - timedelta(seconds=200),
        )
        db.add(device)
        rule = AlertRule(
            name="disabled-rule",
            condition_type="device_offline",
            condition_config={"threshold_seconds": 60},
            severity="warning",
            enabled=False,
            cooldown_seconds=0,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        await db.commit()

    async with Session() as db:
        await run_alert_cycle(db, now)

    from sqlalchemy import select
    async with Session() as db:
        res = await db.execute(select(AlertEvent))
        events = list(res.scalars().all())

    assert len(events) == 0


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_returns_expected_shape():
    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[alerts_router, metrics_router])
    now = datetime.now(timezone.utc)

    # Seed some data
    async with Session() as db:
        db.add(Device(device_uid="d1", is_claimed=True, last_seen_at=now - timedelta(seconds=5)))
        db.add(Device(device_uid="d2", is_claimed=True, last_seen_at=now - timedelta(seconds=200)))
        rule = AlertRule(
            name="r",
            condition_type="device_offline",
            condition_config={},
            severity="warning",
            enabled=True,
            cooldown_seconds=0,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        db.add(AlertEvent(rule_id=rule.id, status="firing", message="x", triggered_at=now))
        await db.commit()

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/metrics", headers=_auth(["metrics.read"]))

    assert resp.status_code == 200
    data = resp.json()
    assert data["devices"]["total"] == 2
    assert data["devices"]["online"] == 1
    assert data["alerts"]["firing"] == 1
    assert data["alerts"]["acknowledged"] == 0
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
