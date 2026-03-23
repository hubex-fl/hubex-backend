"""Tests for Phase 6: OTA firmware/rollout API, edge config/heartbeat, and OTA worker."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.edge import router as edge_router
from app.api.v1.ota import router as ota_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.ota_worker import run_ota_cycle
from app.core.security import hash_device_token
from app.db.base import Base
from app.db.models.device import Device
from app.db.models.events import EventV1
from app.db.models.ota import DeviceOtaStatus, FirmwareVersion, OtaRollout
from app.db.models.pairing import DeviceToken
from tests.conftest import make_token


# ---------------------------------------------------------------------------
# OTA-specific capability map (patched into global for tests)
# ---------------------------------------------------------------------------

_OTA_CAP_MAP: dict[tuple[str, str], list[str]] = {
    ("POST", "/api/v1/ota/firmware"): ["ota.write"],
    ("GET", "/api/v1/ota/firmware"): ["ota.read"],
    ("GET", "/api/v1/ota/firmware/{firmware_id}"): ["ota.read"],
    ("PUT", "/api/v1/ota/firmware/{firmware_id}"): ["ota.write"],
    ("DELETE", "/api/v1/ota/firmware/{firmware_id}"): ["ota.admin"],
    ("POST", "/api/v1/ota/rollouts"): ["ota.write"],
    ("GET", "/api/v1/ota/rollouts"): ["ota.read"],
    ("GET", "/api/v1/ota/rollouts/{rollout_id}"): ["ota.read"],
    ("POST", "/api/v1/ota/rollouts/{rollout_id}/start"): ["ota.write"],
    ("POST", "/api/v1/ota/rollouts/{rollout_id}/pause"): ["ota.write"],
    ("POST", "/api/v1/ota/rollouts/{rollout_id}/cancel"): ["ota.write"],
    ("GET", "/api/v1/ota/check"): ["edge.config"],
    ("GET", "/api/v1/ota/status"): ["edge.config"],
    ("POST", "/api/v1/ota/status/{rollout_id}/ack"): ["edge.config"],
    ("GET", "/api/v1/edge/config"): ["edge.config"],
    ("POST", "/api/v1/edge/heartbeat"): ["edge.config"],
}


@pytest.fixture(autouse=True)
def _cap_map_setup(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP.update(_OTA_CAP_MAP)


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

# Raw DDL for variable tables — avoids JSONB which SQLite can't render.
# Raw DDL for tables that use JSONB (SQLite can't render JSONB via SQLAlchemy DDL).
_EXTRA_DDL = [
    """
    CREATE TABLE IF NOT EXISTS variable_definitions (
        key TEXT PRIMARY KEY,
        scope TEXT NOT NULL,
        value_type TEXT NOT NULL,
        default_value TEXT,
        description TEXT,
        unit TEXT,
        min_value REAL,
        max_value REAL,
        enum_values TEXT,
        regex TEXT,
        is_secret BOOLEAN NOT NULL DEFAULT 0,
        is_readonly BOOLEAN NOT NULL DEFAULT 0,
        user_writable BOOLEAN NOT NULL DEFAULT 1,
        device_writable BOOLEAN NOT NULL DEFAULT 0,
        allow_device_override BOOLEAN NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS variable_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variable_key TEXT NOT NULL,
        scope TEXT NOT NULL,
        device_id INTEGER,
        user_id INTEGER,
        value_json TEXT,
        version INTEGER NOT NULL DEFAULT 1,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_by_user_id INTEGER,
        updated_by_device_id INTEGER,
        UNIQUE(variable_key, device_id, scope, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        execution_context_id INTEGER,
        type TEXT NOT NULL,
        payload TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL,
        priority INTEGER NOT NULL DEFAULT 0,
        idempotency_key TEXT,
        claimed_at DATETIME,
        lease_expires_at DATETIME,
        lease_token TEXT,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at DATETIME,
        result TEXT,
        error TEXT
    )
    """,
]


def _create_tables(metadata, conn) -> None:
    from sqlalchemy import text as _text
    metadata.create_all(
        conn,
        tables=[
            FirmwareVersion.__table__,
            OtaRollout.__table__,
            DeviceOtaStatus.__table__,
            Device.__table__,
            DeviceToken.__table__,
            EventV1.__table__,
        ],
    )
    for ddl in _EXTRA_DDL:
        conn.execute(_text(ddl))


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
    for r in (routers or [ota_router]):
        app.include_router(r, prefix="/api/v1")
    return app


def _auth(caps: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(caps=caps)}"}


def _device_header(token: str) -> dict[str, str]:
    return {"X-Device-Token": token}


async def _seed_device(Session, uid: str = "dev-001", claimed: bool = True) -> tuple[int, str]:
    """Seed a device + active DeviceToken, return (device_id, raw_token)."""
    raw_token = f"raw-{uid}"
    token_hash = hash_device_token(raw_token)
    async with Session() as db:
        device = Device(
            device_uid=uid,
            is_claimed=claimed,
            owner_user_id=1 if claimed else None,
        )
        db.add(device)
        await db.flush()
        dt = DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True)
        db.add(dt)
        await db.commit()
        await db.refresh(device)
        return device.id, raw_token


async def _seed_firmware(Session, version: str = "1.0.0") -> int:
    async with Session() as db:
        fw = FirmwareVersion(
            version=version,
            binary_url=f"https://example.com/{version}.bin",
            checksum_sha256="abc123" * 10,
        )
        db.add(fw)
        await db.commit()
        await db.refresh(fw)
        return fw.id


async def _seed_rollout(
    Session,
    firmware_id: int,
    strategy: str = "staged",
    status: str = "pending",
    target_filter: dict | None = None,
) -> int:
    async with Session() as db:
        rollout = OtaRollout(
            firmware_id=firmware_id,
            name="test-rollout",
            strategy=strategy,
            status=status,
            target_filter=target_filter or {"all": True},
            progress_percent=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(rollout)
        await db.commit()
        await db.refresh(rollout)
        return rollout.id


# ---------------------------------------------------------------------------
# Capability map test
# ---------------------------------------------------------------------------

def test_capability_map_has_ota_entries():
    assert ("POST", "/api/v1/ota/firmware") in CAPABILITY_MAP
    assert ("GET", "/api/v1/ota/rollouts") in CAPABILITY_MAP
    assert ("POST", "/api/v1/ota/rollouts/{rollout_id}/start") in CAPABILITY_MAP
    assert ("GET", "/api/v1/ota/check") in CAPABILITY_MAP
    assert ("GET", "/api/v1/edge/config") in CAPABILITY_MAP
    assert ("POST", "/api/v1/edge/heartbeat") in CAPABILITY_MAP


# ---------------------------------------------------------------------------
# Firmware CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_firmware():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/ota/firmware",
            json={
                "version": "2.1.0",
                "binary_url": "https://example.com/2.1.0.bin",
                "checksum_sha256": "deadbeef" * 8,
            },
            headers=_auth(["ota.write"]),
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == "2.1.0"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_create_firmware_invalid_semver():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/ota/firmware",
            json={
                "version": "not-semver",
                "binary_url": "https://example.com/x.bin",
                "checksum_sha256": "abc",
            },
            headers=_auth(["ota.write"]),
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_firmware_duplicate_version():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    await _seed_firmware(Session, "1.0.0")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/ota/firmware",
            json={"version": "1.0.0", "binary_url": "x", "checksum_sha256": "y"},
            headers=_auth(["ota.write"]),
        )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_firmware():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    await _seed_firmware(Session, "1.0.0")
    await _seed_firmware(Session, "1.1.0")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/ota/firmware", headers=_auth(["ota.read"]))

    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_firmware_not_found():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/ota/firmware/999", headers=_auth(["ota.read"]))

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_firmware():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    fw_id = await _seed_firmware(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.put(
            f"/api/v1/ota/firmware/{fw_id}",
            json={"release_notes": "Bug fixes"},
            headers=_auth(["ota.write"]),
        )

    assert resp.status_code == 200
    assert resp.json()["release_notes"] == "Bug fixes"


@pytest.mark.asyncio
async def test_delete_firmware():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    fw_id = await _seed_firmware(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        del_resp = await c.delete(f"/api/v1/ota/firmware/{fw_id}", headers=_auth(["ota.admin"]))
        get_resp = await c.get(f"/api/v1/ota/firmware/{fw_id}", headers=_auth(["ota.read"]))

    assert del_resp.status_code == 204
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Rollout CRUD + lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rollout():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    fw_id = await _seed_firmware(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/ota/rollouts",
            json={
                "firmware_id": fw_id,
                "name": "My Rollout",
                "strategy": "staged",
                "target_filter": {"all": True},
            },
            headers=_auth(["ota.write"]),
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["strategy"] == "staged"
    assert data["progress_percent"] == 0


@pytest.mark.asyncio
async def test_create_rollout_firmware_not_found():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/ota/rollouts",
            json={"firmware_id": 999, "name": "Bad", "strategy": "immediate"},
            headers=_auth(["ota.write"]),
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rollout_start_pause_cancel_lifecycle():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    fw_id = await _seed_firmware(Session)
    rollout_id = await _seed_rollout(Session, fw_id, status="pending")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        # start pending → active
        r = await c.post(f"/api/v1/ota/rollouts/{rollout_id}/start", headers=_auth(["ota.write"]))
        assert r.status_code == 200
        assert r.json()["status"] == "active"

        # pause active → paused
        r = await c.post(f"/api/v1/ota/rollouts/{rollout_id}/pause", headers=_auth(["ota.write"]))
        assert r.status_code == 200
        assert r.json()["status"] == "paused"

        # re-start paused → active
        r = await c.post(f"/api/v1/ota/rollouts/{rollout_id}/start", headers=_auth(["ota.write"]))
        assert r.status_code == 200
        assert r.json()["status"] == "active"

        # cancel active → failed
        r = await c.post(f"/api/v1/ota/rollouts/{rollout_id}/cancel", headers=_auth(["ota.write"]))
        assert r.status_code == 200
        assert r.json()["status"] == "failed"

        # cancel already-failed → 409
        r = await c.post(f"/api/v1/ota/rollouts/{rollout_id}/cancel", headers=_auth(["ota.write"]))
        assert r.status_code == 409


@pytest.mark.asyncio
async def test_pause_non_active_rollout_returns_409():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    fw_id = await _seed_firmware(Session)
    rollout_id = await _seed_rollout(Session, fw_id, status="pending")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        r = await c.post(f"/api/v1/ota/rollouts/{rollout_id}/pause", headers=_auth(["ota.write"]))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_rollouts_filter_by_status():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    fw_id = await _seed_firmware(Session)
    await _seed_rollout(Session, fw_id, status="pending")
    await _seed_rollout(Session, fw_id, status="active")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        all_r = await c.get("/api/v1/ota/rollouts", headers=_auth(["ota.read"]))
        pending_r = await c.get("/api/v1/ota/rollouts?status=pending", headers=_auth(["ota.read"]))
        active_r = await c.get("/api/v1/ota/rollouts?status=active", headers=_auth(["ota.read"]))

    assert len(all_r.json()) == 2
    assert len(pending_r.json()) == 1
    assert len(active_r.json()) == 1


# ---------------------------------------------------------------------------
# Device OTA check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ota_check_no_update():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    device_id, raw_token = await _seed_device(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/ota/check", headers=_device_header(raw_token))

    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_ota_check_returns_pending_update():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    device_id, raw_token = await _seed_device(Session)
    fw_id = await _seed_firmware(Session, "3.0.0")
    rollout_id = await _seed_rollout(Session, fw_id, status="active")

    # Assign device to rollout
    async with Session() as db:
        db.add(DeviceOtaStatus(
            device_id=device_id,
            rollout_id=rollout_id,
            firmware_id=fw_id,
            status="pending",
        ))
        await db.commit()

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/ota/check", headers=_device_header(raw_token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "3.0.0"
    assert data["rollout_id"] == rollout_id
    assert "binary_url" in data
    assert "checksum_sha256" in data


@pytest.mark.asyncio
async def test_ota_check_ignores_paused_rollout():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    device_id, raw_token = await _seed_device(Session)
    fw_id = await _seed_firmware(Session)
    rollout_id = await _seed_rollout(Session, fw_id, status="paused")

    async with Session() as db:
        db.add(DeviceOtaStatus(
            device_id=device_id,
            rollout_id=rollout_id,
            firmware_id=fw_id,
            status="pending",
        ))
        await db.commit()

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/ota/check", headers=_device_header(raw_token))

    assert resp.status_code == 200
    assert resp.json() is None


# ---------------------------------------------------------------------------
# Device OTA status ack
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ota_ack_updates_status():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    device_id, raw_token = await _seed_device(Session)
    fw_id = await _seed_firmware(Session)
    rollout_id = await _seed_rollout(Session, fw_id, status="active")

    async with Session() as db:
        db.add(DeviceOtaStatus(
            device_id=device_id,
            rollout_id=rollout_id,
            firmware_id=fw_id,
            status="pending",
        ))
        await db.commit()

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/ota/status/{rollout_id}/ack",
            json={"status": "done"},
            headers=_device_header(raw_token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["finished_at"] is not None


@pytest.mark.asyncio
async def test_ota_ack_not_found():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    device_id, raw_token = await _seed_device(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/ota/status/999/ack",
            json={"status": "done"},
            headers=_device_header(raw_token),
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ota_ack_records_error_msg():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    device_id, raw_token = await _seed_device(Session)
    fw_id = await _seed_firmware(Session)
    rollout_id = await _seed_rollout(Session, fw_id, status="active")

    async with Session() as db:
        db.add(DeviceOtaStatus(
            device_id=device_id, rollout_id=rollout_id, firmware_id=fw_id, status="pending",
        ))
        await db.commit()

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/ota/status/{rollout_id}/ack",
            json={"status": "failed", "error_msg": "checksum mismatch"},
            headers=_device_header(raw_token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["error_msg"] == "checksum mismatch"


# ---------------------------------------------------------------------------
# Edge config & heartbeat
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_edge_config_empty():
    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[edge_router])
    device_id, raw_token = await _seed_device(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/edge/config", headers=_device_header(raw_token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == device_id
    assert data["variables"] == {}
    assert data["tasks"] == []


@pytest.mark.asyncio
async def test_edge_config_returns_variables_and_tasks():
    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[edge_router])
    device_id, raw_token = await _seed_device(Session)

    async with Session() as db:
        from sqlalchemy import text as _text
        # Seed variable definition + value via raw SQL (avoids JSONB on SQLite)
        await db.execute(_text(
            "INSERT INTO variable_definitions (key, scope, value_type) VALUES ('poll_interval', 'device', 'int')"
        ))
        await db.execute(_text(
            f"INSERT INTO variable_values (variable_key, scope, device_id, value_json) VALUES ('poll_interval', 'device', {device_id}, '30')"
        ))
        # Seed pending task via raw SQL (Task model uses JSONB)
        await db.execute(_text(
            f"INSERT INTO tasks (client_id, type, payload, status, priority) "
            f"VALUES ({device_id}, 'reboot', '{{\"reason\": \"scheduled\"}}', 'pending', 1)"
        ))
        await db.commit()

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get("/api/v1/edge/config", headers=_device_header(raw_token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["variables"]["poll_interval"] == 30
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["type"] == "reboot"


@pytest.mark.asyncio
async def test_edge_heartbeat_updates_last_seen():
    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[edge_router])
    device_id, raw_token = await _seed_device(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/edge/heartbeat",
            json={"firmware_version": "2.0.1"},
            headers=_device_header(raw_token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == device_id
    assert data["last_seen_at"] is not None

    async with Session() as db:
        dev = await db.get(Device, device_id)
        assert dev.last_seen_at is not None
        assert dev.firmware_version == "2.0.1"


@pytest.mark.asyncio
async def test_edge_heartbeat_no_firmware_version():
    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[edge_router])
    device_id, raw_token = await _seed_device(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post("/api/v1/edge/heartbeat", json={}, headers=_device_header(raw_token))

    assert resp.status_code == 200

    async with Session() as db:
        dev = await db.get(Device, device_id)
        assert dev.last_seen_at is not None
        assert dev.firmware_version is None  # not set


# ---------------------------------------------------------------------------
# OTA Worker — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_immediate_assigns_all_devices():
    _, Session = await _mk_session()
    now = datetime.now(timezone.utc)

    # Seed 3 devices
    ids = []
    for i in range(3):
        dev_id, _ = await _seed_device(Session, uid=f"dev-imm-{i}")
        ids.append(dev_id)

    fw_id = await _seed_firmware(Session, "5.0.0")
    rollout_id = await _seed_rollout(
        Session, fw_id, strategy="immediate", status="active",
        target_filter={"device_ids": ids},
    )

    async with Session() as db:
        await run_ota_cycle(db)

    async with Session() as db:
        res = await db.execute(
            select(DeviceOtaStatus).where(DeviceOtaStatus.rollout_id == rollout_id)
        )
        statuses = list(res.scalars().all())

    assert len(statuses) == 3
    assert all(s.status == "pending" for s in statuses)


@pytest.mark.asyncio
async def test_worker_staged_assigns_10_percent():
    _, Session = await _mk_session()

    # Seed 20 devices
    ids = []
    for i in range(20):
        dev_id, _ = await _seed_device(Session, uid=f"dev-staged-{i}")
        ids.append(dev_id)

    fw_id = await _seed_firmware(Session, "6.0.0")
    rollout_id = await _seed_rollout(
        Session, fw_id, strategy="staged", status="active",
        target_filter={"device_ids": ids},
    )

    async with Session() as db:
        await run_ota_cycle(db)

    async with Session() as db:
        res = await db.execute(
            select(DeviceOtaStatus).where(DeviceOtaStatus.rollout_id == rollout_id)
        )
        statuses = list(res.scalars().all())

    # 10% of 20 = 2 devices assigned in first batch
    assert len(statuses) == 2


@pytest.mark.asyncio
async def test_worker_expands_staged_batch_after_completion():
    _, Session = await _mk_session()

    # 10 devices → batch size 1
    ids = []
    for i in range(10):
        dev_id, _ = await _seed_device(Session, uid=f"dev-expand-{i}")
        ids.append(dev_id)

    fw_id = await _seed_firmware(Session, "7.0.0")
    rollout_id = await _seed_rollout(
        Session, fw_id, strategy="staged", status="active",
        target_filter={"device_ids": ids},
    )

    # First cycle: assigns 1 device (10% of 10)
    async with Session() as db:
        await run_ota_cycle(db)

    async with Session() as db:
        res = await db.execute(
            select(DeviceOtaStatus).where(DeviceOtaStatus.rollout_id == rollout_id)
        )
        first_batch = list(res.scalars().all())

    assert len(first_batch) == 1

    # Simulate device completing update
    async with Session() as db:
        res = await db.execute(
            select(DeviceOtaStatus).where(DeviceOtaStatus.rollout_id == rollout_id)
        )
        dos = res.scalar_one()
        dos.status = "done"
        await db.commit()

    # Second cycle: should assign next batch
    async with Session() as db:
        await run_ota_cycle(db)

    async with Session() as db:
        res = await db.execute(
            select(DeviceOtaStatus).where(DeviceOtaStatus.rollout_id == rollout_id)
        )
        second_batch = list(res.scalars().all())

    assert len(second_batch) == 2  # 1 done + 1 new


@pytest.mark.asyncio
async def test_worker_marks_rollout_completed():
    _, Session = await _mk_session()

    dev_id, _ = await _seed_device(Session, uid="dev-complete")
    fw_id = await _seed_firmware(Session, "8.0.0")
    rollout_id = await _seed_rollout(
        Session, fw_id, strategy="immediate", status="active",
        target_filter={"device_ids": [dev_id]},
    )

    # First cycle: assigns device
    async with Session() as db:
        await run_ota_cycle(db)

    # Device completes
    async with Session() as db:
        res = await db.execute(
            select(DeviceOtaStatus).where(DeviceOtaStatus.rollout_id == rollout_id)
        )
        dos = res.scalar_one()
        dos.status = "done"
        await db.commit()

    # Second cycle: should mark rollout completed
    async with Session() as db:
        await run_ota_cycle(db)

    async with Session() as db:
        rollout = await db.get(OtaRollout, rollout_id)

    assert rollout.status == "completed"
    assert rollout.progress_percent == 100


@pytest.mark.asyncio
async def test_worker_skips_paused_rollouts():
    _, Session = await _mk_session()

    dev_id, _ = await _seed_device(Session, uid="dev-paused")
    fw_id = await _seed_firmware(Session, "9.0.0")
    rollout_id = await _seed_rollout(
        Session, fw_id, strategy="immediate", status="paused",
        target_filter={"device_ids": [dev_id]},
    )

    async with Session() as db:
        await run_ota_cycle(db)

    async with Session() as db:
        res = await db.execute(
            select(DeviceOtaStatus).where(DeviceOtaStatus.rollout_id == rollout_id)
        )
        statuses = list(res.scalars().all())

    # Paused rollout should not get any devices assigned
    assert len(statuses) == 0


@pytest.mark.asyncio
async def test_worker_empty_target_completes_rollout():
    _, Session = await _mk_session()

    fw_id = await _seed_firmware(Session, "10.0.0")
    rollout_id = await _seed_rollout(
        Session, fw_id, strategy="immediate", status="active",
        target_filter={"device_ids": []},
    )

    async with Session() as db:
        await run_ota_cycle(db)

    async with Session() as db:
        rollout = await db.get(OtaRollout, rollout_id)

    assert rollout.status == "completed"
    assert rollout.progress_percent == 100


# ---------------------------------------------------------------------------
# System events emitted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_firmware_emits_event():
    _, Session = await _mk_session()
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        await c.post(
            "/api/v1/ota/firmware",
            json={"version": "11.0.0", "binary_url": "u", "checksum_sha256": "c"},
            headers=_auth(["ota.write"]),
        )

    async with Session() as db:
        res = await db.execute(
            select(EventV1).where(EventV1.type == "ota.firmware.created")
        )
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].payload["version"] == "11.0.0"


@pytest.mark.asyncio
async def test_start_rollout_emits_event():
    _, Session = await _mk_session()
    app = await _mk_app(Session)
    fw_id = await _seed_firmware(Session)
    rollout_id = await _seed_rollout(Session, fw_id, status="pending")

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        await c.post(f"/api/v1/ota/rollouts/{rollout_id}/start", headers=_auth(["ota.write"]))

    async with Session() as db:
        res = await db.execute(
            select(EventV1).where(EventV1.type == "ota.rollout.started")
        )
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].payload["rollout_id"] == rollout_id
