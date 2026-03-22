"""Tests for Entity CRUD, device binding management, groups, health, and system events."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.entities import router as entities_router
from app.api.v1.groups import router as groups_router
from app.core.capabilities import CAPABILITY_MAP
from app.db.base import Base
from app.db.models.device import Device
from app.db.models.entities import Entity, EntityDeviceBinding
from app.db.models.events import EventV1
from tests.conftest import make_token


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            Device.__table__,
            Entity.__table__,
            EntityDeviceBinding.__table__,
            EventV1.__table__,
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
    for r in (routers or [entities_router]):
        app.include_router(r, prefix="/api/v1")
    return app


def _auth(caps: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(caps=caps)}"}


async def _seed_device(Session, device_uid: str = "dev-001", last_seen_offset_seconds: int = 0):
    """Insert a Device row and return its id."""
    now = datetime.now(timezone.utc)
    last_seen = now - timedelta(seconds=abs(last_seen_offset_seconds)) if last_seen_offset_seconds >= 0 else None
    async with Session() as db:
        device = Device(device_uid=device_uid, last_seen_at=last_seen, is_claimed=False)
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device.id


# ---------------------------------------------------------------------------
# Entity CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_entity(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/entities")] = ["entities.write"]
    CAPABILITY_MAP[("GET", "/api/v1/entities/{entity_id}")] = ["entities.read"]

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-001", "type": "sensor", "name": "Temp Sensor", "tags": {"floor": 2}},
            headers=_auth(["entities.write"]),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["entity_id"] == "ent-001"
    assert data["type"] == "sensor"
    assert data["name"] == "Temp Sensor"
    assert data["tags"] == {"floor": 2}


@pytest.mark.asyncio
async def test_create_entity_idempotent(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/entities")] = ["entities.write"]

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-idem", "type": "group"},
            headers=_auth(["entities.write"]),
        )
        assert r1.status_code == 201

        r2 = await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-idem", "type": "group"},
            headers=_auth(["entities.write"]),
        )
        assert r2.status_code == 200
        assert r2.json()["entity_id"] == "ent-idem"


@pytest.mark.asyncio
async def test_update_entity(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/entities")] = ["entities.write"]
    CAPABILITY_MAP[("PUT", "/api/v1/entities/{entity_id}")] = ["entities.write"]
    CAPABILITY_MAP[("GET", "/api/v1/entities/{entity_id}")] = ["entities.read"]

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-upd", "type": "sensor", "name": "Old"},
            headers=_auth(["entities.write"]),
        )
        resp = await client.put(
            "/api/v1/entities/ent-upd",
            json={"name": "New Name", "tags": ["a", "b"]},
            headers=_auth(["entities.write"]),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["tags"] == ["a", "b"]


@pytest.mark.asyncio
async def test_update_entity_not_found(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("PUT", "/api/v1/entities/{entity_id}")] = ["entities.write"]

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put(
            "/api/v1/entities/nonexistent",
            json={"name": "X"},
            headers=_auth(["entities.write"]),
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/entities")] = ["entities.write"]
    CAPABILITY_MAP[("DELETE", "/api/v1/entities/{entity_id}")] = ["entities.write"]
    CAPABILITY_MAP[("GET", "/api/v1/entities/{entity_id}")] = ["entities.read"]

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-del", "type": "sensor"},
            headers=_auth(["entities.write"]),
        )
        del_resp = await client.delete(
            "/api/v1/entities/ent-del",
            headers=_auth(["entities.write"]),
        )
        assert del_resp.status_code == 204

        get_resp = await client.get(
            "/api/v1/entities/ent-del",
            headers=_auth(["entities.read"]),
        )
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_entity_cascades_bindings(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    device_id = await _seed_device(Session, "dev-casc")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-casc", "type": "group"},
            headers=_auth(["entities.write"]),
        )
        await client.post(
            "/api/v1/entities/ent-casc/devices",
            json={"device_ids": [device_id]},
            headers=_auth(["entities.write"]),
        )
        await client.delete(
            "/api/v1/entities/ent-casc",
            headers=_auth(["entities.write"]),
        )
        # Entity is gone
        get_resp = await client.get(
            "/api/v1/entities/ent-casc",
            headers=_auth(["entities.read"]),
        )
        assert get_resp.status_code == 404
        # Bindings are cascade-deleted (empty list)
        list_resp = await client.get(
            "/api/v1/entities/ent-casc/devices",
            headers=_auth(["entities.read"]),
        )
        assert list_resp.json() == []


# ---------------------------------------------------------------------------
# Device binding tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bind_and_unbind_device(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    device_id = await _seed_device(Session, "dev-bind")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-b", "type": "sensor"},
            headers=_auth(["entities.write"]),
        )
        bind_resp = await client.post(
            "/api/v1/entities/ent-b/devices",
            json={"device_ids": [device_id], "priority": 5, "enabled": True},
            headers=_auth(["entities.write"]),
        )
        assert bind_resp.status_code == 201
        bindings = bind_resp.json()
        assert len(bindings) == 1
        assert bindings[0]["device_id"] == device_id
        assert bindings[0]["priority"] == 5

        list_resp = await client.get(
            f"/api/v1/entities/ent-b/devices",
            headers=_auth(["entities.read"]),
        )
        assert len(list_resp.json()) == 1

        unbind_resp = await client.delete(
            f"/api/v1/entities/ent-b/devices/{device_id}",
            headers=_auth(["entities.write"]),
        )
        assert unbind_resp.status_code == 204

        list_resp2 = await client.get(
            f"/api/v1/entities/ent-b/devices",
            headers=_auth(["entities.read"]),
        )
        assert list_resp2.json() == []


@pytest.mark.asyncio
async def test_bind_duplicate_rejected(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    device_id = await _seed_device(Session, "dev-dup")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-dup", "type": "group"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/ent-dup/devices",
            json={"device_ids": [device_id]},
            headers=_auth([]),
        )
        resp = await client.post(
            "/api/v1/entities/ent-dup/devices",
            json={"device_ids": [device_id]},
            headers=_auth([]),
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_bind_nonexistent_device(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-nodev", "type": "group"},
            headers=_auth([]),
        )
        resp = await client.post(
            "/api/v1/entities/ent-nodev/devices",
            json={"device_ids": [99999]},
            headers=_auth([]),
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_binding_priority(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    device_id = await _seed_device(Session, "dev-upd")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-upd2", "type": "sensor"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/ent-upd2/devices",
            json={"device_ids": [device_id], "priority": 0},
            headers=_auth([]),
        )
        resp = await client.put(
            f"/api/v1/entities/ent-upd2/devices/{device_id}",
            json={"priority": 10, "enabled": False},
            headers=_auth([]),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["priority"] == 10
    assert data["enabled"] is False


# ---------------------------------------------------------------------------
# Bulk bind / unbind tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bulk_bind(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    d1 = await _seed_device(Session, "dev-bulk-1")
    d2 = await _seed_device(Session, "dev-bulk-2")
    d3 = await _seed_device(Session, "dev-bulk-3")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-bulk", "type": "group"},
            headers=_auth([]),
        )
        resp = await client.post(
            "/api/v1/entities/ent-bulk/devices/bulk-bind",
            json={"device_ids": [d1, d2, d3]},
            headers=_auth([]),
        )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert all(r["ok"] for r in results)


@pytest.mark.asyncio
async def test_bulk_bind_partial_failure(monkeypatch):
    """Bulk bind with one nonexistent device — others succeed."""
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    d1 = await _seed_device(Session, "dev-pf-1")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-pf", "type": "group"},
            headers=_auth([]),
        )
        resp = await client.post(
            "/api/v1/entities/ent-pf/devices/bulk-bind",
            json={"device_ids": [d1, 99999]},
            headers=_auth([]),
        )
    assert resp.status_code == 200
    results = resp.json()["results"]
    ok_results = [r for r in results if r["ok"]]
    fail_results = [r for r in results if not r["ok"]]
    assert len(ok_results) == 1
    assert len(fail_results) == 1
    assert fail_results[0]["device_id"] == 99999


@pytest.mark.asyncio
async def test_bulk_unbind(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    d1 = await _seed_device(Session, "dev-ubd-1")
    d2 = await _seed_device(Session, "dev-ubd-2")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-ubd", "type": "group"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/ent-ubd/devices/bulk-bind",
            json={"device_ids": [d1, d2]},
            headers=_auth([]),
        )
        resp = await client.post(
            "/api/v1/entities/ent-ubd/devices/bulk-unbind",
            json={"device_ids": [d1, d2]},
            headers=_auth([]),
        )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert all(r["ok"] for r in results)


@pytest.mark.asyncio
async def test_bulk_unbind_already_not_bound(monkeypatch):
    """Bulk unbind with one device not bound — that one fails, others succeed."""
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    d1 = await _seed_device(Session, "dev-unb-1")
    d2 = await _seed_device(Session, "dev-unb-2")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-unb", "type": "group"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/ent-unb/devices/bulk-bind",
            json={"device_ids": [d1]},
            headers=_auth([]),
        )
        resp = await client.post(
            "/api/v1/entities/ent-unb/devices/bulk-unbind",
            json={"device_ids": [d1, d2]},
            headers=_auth([]),
        )
    assert resp.status_code == 200
    results = resp.json()["results"]
    ok_results = [r for r in results if r["ok"]]
    fail_results = [r for r in results if not r["ok"]]
    assert len(ok_results) == 1
    assert ok_results[0]["device_id"] == d1
    assert len(fail_results) == 1
    assert fail_results[0]["device_id"] == d2


# ---------------------------------------------------------------------------
# Groups tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_groups(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/groups")] = ["groups.read"]
    CAPABILITY_MAP[("POST", "/api/v1/entities")] = ["entities.write"]

    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[entities_router, groups_router])
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "g-1", "type": "group"},
            headers=_auth(["entities.write"]),
        )
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "s-1", "type": "sensor"},
            headers=_auth(["entities.write"]),
        )
        resp = await client.get("/api/v1/groups", headers=_auth(["groups.read"]))

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["entity_id"] == "g-1"
    assert items[0]["type"] == "group"


@pytest.mark.asyncio
async def test_create_group(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/groups")] = ["groups.write"]

    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[entities_router, groups_router])
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/groups",
            json={"entity_id": "grp-new", "name": "My Group"},
            headers=_auth(["groups.write"]),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["entity_id"] == "grp-new"
    assert data["type"] == "group"
    assert data["name"] == "My Group"


@pytest.mark.asyncio
async def test_create_group_idempotent(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/groups")] = ["groups.write"]

    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[entities_router, groups_router])
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/groups",
            json={"entity_id": "grp-idem"},
            headers=_auth(["groups.write"]),
        )
        r2 = await client.post(
            "/api/v1/groups",
            json={"entity_id": "grp-idem"},
            headers=_auth(["groups.write"]),
        )
    assert r1.status_code == 201
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_list_group_devices(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    device_id = await _seed_device(Session, "dev-grp")
    app = await _mk_app(Session, routers=[entities_router, groups_router])
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/groups",
            json={"entity_id": "grp-devs"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/grp-devs/devices",
            json={"device_ids": [device_id]},
            headers=_auth([]),
        )
        resp = await client.get(
            "/api/v1/groups/grp-devs/devices",
            headers=_auth([]),
        )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["device_id"] == device_id


# ---------------------------------------------------------------------------
# Health aggregation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_entity_health_all_online(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    # Devices seen 5 seconds ago (online)
    d1 = await _seed_device(Session, "dev-h1", last_seen_offset_seconds=5)
    d2 = await _seed_device(Session, "dev-h2", last_seen_offset_seconds=10)
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-health", "type": "group"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/ent-health/devices/bulk-bind",
            json={"device_ids": [d1, d2]},
            headers=_auth([]),
        )
        resp = await client.get(
            "/api/v1/entities/ent-health/health",
            headers=_auth([]),
        )
    assert resp.status_code == 200
    h = resp.json()
    assert h["entity_id"] == "ent-health"
    assert h["device_count"] == 2
    assert h["online"] == 2
    assert h["stale"] == 0
    assert h["offline"] == 0
    assert h["worst_health"] == "ok"


@pytest.mark.asyncio
async def test_entity_health_mixed(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    d_online = await _seed_device(Session, "dev-mx1", last_seen_offset_seconds=5)    # online
    d_stale = await _seed_device(Session, "dev-mx2", last_seen_offset_seconds=60)   # stale
    d_offline = await _seed_device(Session, "dev-mx3", last_seen_offset_seconds=300) # offline
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-mixed", "type": "group"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/ent-mixed/devices/bulk-bind",
            json={"device_ids": [d_online, d_stale, d_offline]},
            headers=_auth([]),
        )
        resp = await client.get(
            "/api/v1/entities/ent-mixed/health",
            headers=_auth([]),
        )
    assert resp.status_code == 200
    h = resp.json()
    assert h["device_count"] == 3
    assert h["online"] == 1
    assert h["stale"] == 1
    assert h["offline"] == 1
    assert h["worst_health"] == "offline"


@pytest.mark.asyncio
async def test_entity_health_no_devices(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-empty", "type": "group"},
            headers=_auth([]),
        )
        resp = await client.get(
            "/api/v1/entities/ent-empty/health",
            headers=_auth([]),
        )
    assert resp.status_code == 200
    h = resp.json()
    assert h["device_count"] == 0
    assert h["worst_health"] == "unknown"


# ---------------------------------------------------------------------------
# Capability enforcement tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_entities_write_cap_enforced(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/entities")] = ["entities.write"]

    _, Session = await _mk_session()
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # No token
        r1 = await client.post(
            "/api/v1/entities",
            json={"entity_id": "x", "type": "group"},
        )
        assert r1.status_code == 401

        # Wrong cap
        r2 = await client.post(
            "/api/v1/entities",
            json={"entity_id": "x", "type": "group"},
            headers=_auth(["entities.read"]),
        )
        assert r2.status_code == 403

        # Correct cap
        r3 = await client.post(
            "/api/v1/entities",
            json={"entity_id": "x", "type": "group"},
            headers=_auth(["entities.write"]),
        )
        assert r3.status_code == 201


# ---------------------------------------------------------------------------
# System events test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_system_events_emitted(monkeypatch):
    """entity.created, entity.device.bound, entity.device.unbound are emitted."""
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")
    from sqlalchemy import select as sa_select
    from app.db.models.events import EventV1

    _, Session = await _mk_session()
    device_id = await _seed_device(Session, "dev-evt")
    app = await _mk_app(Session)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/entities",
            json={"entity_id": "ent-evt", "type": "group"},
            headers=_auth([]),
        )
        await client.post(
            "/api/v1/entities/ent-evt/devices",
            json={"device_ids": [device_id]},
            headers=_auth([]),
        )
        await client.delete(
            f"/api/v1/entities/ent-evt/devices/{device_id}",
            headers=_auth([]),
        )

    async with Session() as db:
        res = await db.execute(sa_select(EventV1).order_by(EventV1.id))
        events = res.scalars().all()

    event_types = [e.type for e in events]
    assert "entity.created" in event_types
    assert "entity.device.bound" in event_types
    assert "entity.device.unbound" in event_types
