"""OTA Firmware & Rollout API.

Firmware CRUD:       POST/GET/PUT/DELETE /ota/firmware
Rollout CRUD:        POST/GET            /ota/rollouts
Rollout lifecycle:   POST /ota/rollouts/{id}/start|pause|cancel
Device OTA check:    GET  /ota/check               (X-Device-Token)
Device OTA status:   GET  /ota/status              (X-Device-Token)
Device OTA ack:      POST /ota/status/{rollout_id}/ack (X-Device-Token)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device
from app.api.deps_org import get_current_org_id
from app.core.system_events import emit_system_event
from app.db.models.device import Device
from app.db.models.ota import DeviceOtaStatus, FirmwareVersion, OtaRollout

router = APIRouter(prefix="/ota")

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")
_VALID_STRATEGIES = {"immediate", "staged", "canary"}
_VALID_ROLLOUT_STATUSES = {"pending", "active", "paused", "completed", "failed"}
_TERMINAL_STATUSES = {"done", "failed", "skipped"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FirmwareVersionCreate(BaseModel):
    version: str
    binary_url: str
    checksum_sha256: str
    release_notes: str | None = None
    min_hw_version: str | None = None

    @field_validator("version")
    @classmethod
    def _validate_semver(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError("version must be semver (e.g. 1.2.3)")
        return v


class FirmwareVersionUpdate(BaseModel):
    binary_url: str | None = None
    checksum_sha256: str | None = None
    release_notes: str | None = None
    min_hw_version: str | None = None


class FirmwareVersionOut(BaseModel):
    id: int
    version: str
    binary_url: str
    checksum_sha256: str
    release_notes: str | None
    min_hw_version: str | None
    org_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OtaRolloutCreate(BaseModel):
    firmware_id: int
    name: str
    strategy: Literal["immediate", "staged", "canary"]
    target_filter: dict[str, Any] | None = None


class OtaRolloutOut(BaseModel):
    id: int
    firmware_id: int
    name: str
    strategy: str
    target_filter: dict[str, Any] | None
    progress_percent: int
    status: str
    org_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeviceOtaStatusOut(BaseModel):
    id: int
    device_id: int
    rollout_id: int
    firmware_id: int
    status: str
    error_msg: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class OtaCheckOut(BaseModel):
    rollout_id: int
    firmware_id: int
    version: str
    binary_url: str
    checksum_sha256: str


class DeviceOtaAck(BaseModel):
    status: Literal["downloading", "flashing", "done", "failed", "skipped"]
    error_msg: str | None = None


# ---------------------------------------------------------------------------
# Firmware CRUD
# ---------------------------------------------------------------------------

@router.post("/firmware", response_model=FirmwareVersionOut, status_code=201)
async def create_firmware(
    body: FirmwareVersionCreate,
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    # Version must be unique
    existing = await db.execute(
        select(FirmwareVersion).where(FirmwareVersion.version == body.version)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, detail="firmware version already exists")

    fw = FirmwareVersion(
        version=body.version,
        binary_url=body.binary_url,
        checksum_sha256=body.checksum_sha256,
        release_notes=body.release_notes,
        min_hw_version=body.min_hw_version,
        org_id=org_id,
    )
    db.add(fw)
    await db.flush()
    await emit_system_event(db, "ota.firmware.created", {
        "firmware_id": fw.id, "version": fw.version,
    })
    await db.commit()
    await db.refresh(fw)
    return fw


@router.get("/firmware", response_model=list[FirmwareVersionOut])
async def list_firmware(
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    stmt = select(FirmwareVersion)
    if org_id is not None:
        stmt = stmt.where(FirmwareVersion.org_id == org_id)
    res = await db.execute(stmt.order_by(FirmwareVersion.created_at.desc()))
    return list(res.scalars().all())


@router.get("/firmware/{firmware_id}", response_model=FirmwareVersionOut)
async def get_firmware(firmware_id: int, db: AsyncSession = Depends(get_db)):
    fw = await db.get(FirmwareVersion, firmware_id)
    if fw is None:
        raise HTTPException(404, detail="firmware not found")
    return fw


@router.put("/firmware/{firmware_id}", response_model=FirmwareVersionOut)
async def update_firmware(
    firmware_id: int,
    body: FirmwareVersionUpdate,
    db: AsyncSession = Depends(get_db),
):
    fw = await db.get(FirmwareVersion, firmware_id)
    if fw is None:
        raise HTTPException(404, detail="firmware not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(fw, field, value)
    await db.commit()
    await db.refresh(fw)
    return fw


@router.delete("/firmware/{firmware_id}", status_code=204)
async def delete_firmware(firmware_id: int, db: AsyncSession = Depends(get_db)):
    fw = await db.get(FirmwareVersion, firmware_id)
    if fw is None:
        raise HTTPException(404, detail="firmware not found")
    await db.delete(fw)
    await db.commit()


# ---------------------------------------------------------------------------
# Rollout CRUD + lifecycle
# ---------------------------------------------------------------------------

@router.post("/rollouts", response_model=OtaRolloutOut, status_code=201)
async def create_rollout(
    body: OtaRolloutCreate,
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
):
    fw = await db.get(FirmwareVersion, body.firmware_id)
    if fw is None:
        raise HTTPException(404, detail="firmware not found")

    rollout = OtaRollout(
        firmware_id=body.firmware_id,
        name=body.name,
        strategy=body.strategy,
        target_filter=body.target_filter,
        status="pending",
        progress_percent=0,
        org_id=org_id,
    )
    db.add(rollout)
    await db.flush()
    await emit_system_event(db, "ota.rollout.created", {
        "rollout_id": rollout.id, "name": rollout.name, "strategy": rollout.strategy,
    })
    await db.commit()
    await db.refresh(rollout)
    return rollout


@router.get("/rollouts", response_model=list[OtaRolloutOut])
async def list_rollouts(
    db: AsyncSession = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    status: str | None = None,
):
    stmt = select(OtaRollout)
    if org_id is not None:
        stmt = stmt.where(OtaRollout.org_id == org_id)
    if status:
        stmt = stmt.where(OtaRollout.status == status)
    res = await db.execute(stmt.order_by(OtaRollout.created_at.desc()))
    return list(res.scalars().all())


@router.get("/rollouts/{rollout_id}", response_model=OtaRolloutOut)
async def get_rollout(rollout_id: int, db: AsyncSession = Depends(get_db)):
    rollout = await db.get(OtaRollout, rollout_id)
    if rollout is None:
        raise HTTPException(404, detail="rollout not found")
    return rollout


@router.post("/rollouts/{rollout_id}/start", response_model=OtaRolloutOut)
async def start_rollout(rollout_id: int, db: AsyncSession = Depends(get_db)):
    rollout = await db.get(OtaRollout, rollout_id)
    if rollout is None:
        raise HTTPException(404, detail="rollout not found")
    if rollout.status not in ("pending", "paused"):
        raise HTTPException(409, detail=f"cannot start rollout in status '{rollout.status}'")
    rollout.status = "active"
    rollout.updated_at = datetime.now(timezone.utc)
    await emit_system_event(db, "ota.rollout.started", {
        "rollout_id": rollout.id, "name": rollout.name,
    })
    await db.commit()
    await db.refresh(rollout)
    return rollout


@router.post("/rollouts/{rollout_id}/pause", response_model=OtaRolloutOut)
async def pause_rollout(rollout_id: int, db: AsyncSession = Depends(get_db)):
    rollout = await db.get(OtaRollout, rollout_id)
    if rollout is None:
        raise HTTPException(404, detail="rollout not found")
    if rollout.status != "active":
        raise HTTPException(409, detail="only active rollouts can be paused")
    rollout.status = "paused"
    rollout.updated_at = datetime.now(timezone.utc)
    await emit_system_event(db, "ota.rollout.paused", {"rollout_id": rollout.id})
    await db.commit()
    await db.refresh(rollout)
    return rollout


@router.post("/rollouts/{rollout_id}/cancel", response_model=OtaRolloutOut)
async def cancel_rollout(rollout_id: int, db: AsyncSession = Depends(get_db)):
    rollout = await db.get(OtaRollout, rollout_id)
    if rollout is None:
        raise HTTPException(404, detail="rollout not found")
    if rollout.status in ("completed", "failed"):
        raise HTTPException(409, detail="rollout already finished")
    rollout.status = "failed"
    rollout.updated_at = datetime.now(timezone.utc)
    await emit_system_event(db, "ota.rollout.cancelled", {"rollout_id": rollout.id})
    await db.commit()
    await db.refresh(rollout)
    return rollout


# ---------------------------------------------------------------------------
# Device OTA check (X-Device-Token auth)
# ---------------------------------------------------------------------------

@router.get("/check")
async def ota_check(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    """Return a pending OTA update for this device, or 204 if none."""
    res = await db.execute(
        select(DeviceOtaStatus, OtaRollout, FirmwareVersion)
        .join(OtaRollout, OtaRollout.id == DeviceOtaStatus.rollout_id)
        .join(FirmwareVersion, FirmwareVersion.id == DeviceOtaStatus.firmware_id)
        .where(
            DeviceOtaStatus.device_id == device.id,
            DeviceOtaStatus.status == "pending",
            OtaRollout.status == "active",
        )
        .order_by(OtaRollout.created_at.asc())
        .limit(1)
    )
    row = res.first()
    if row is None:
        return None  # FastAPI returns 200 with null body; caller checks

    dos, rollout, fw = row
    return OtaCheckOut(
        rollout_id=rollout.id,
        firmware_id=fw.id,
        version=fw.version,
        binary_url=fw.binary_url,
        checksum_sha256=fw.checksum_sha256,
    )


# ---------------------------------------------------------------------------
# Device OTA status list + ack (X-Device-Token auth)
# ---------------------------------------------------------------------------

@router.get("/status", response_model=list[DeviceOtaStatusOut])
async def list_device_ota_status(
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(DeviceOtaStatus)
        .where(DeviceOtaStatus.device_id == device.id)
        .order_by(DeviceOtaStatus.id.desc())
    )
    return list(res.scalars().all())


@router.post("/status/{rollout_id}/ack", response_model=DeviceOtaStatusOut)
async def ack_ota_status(
    rollout_id: int,
    body: DeviceOtaAck,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(DeviceOtaStatus).where(
            DeviceOtaStatus.device_id == device.id,
            DeviceOtaStatus.rollout_id == rollout_id,
        )
    )
    dos = res.scalar_one_or_none()
    if dos is None:
        raise HTTPException(404, detail="no OTA status for this rollout")

    now = datetime.now(timezone.utc)
    dos.status = body.status
    if body.error_msg is not None:
        dos.error_msg = body.error_msg
    if body.status == "downloading" and dos.started_at is None:
        dos.started_at = now
    if body.status in _TERMINAL_STATUSES:
        dos.finished_at = now

    await emit_system_event(db, "ota.device.status", {
        "device_id": device.id,
        "rollout_id": rollout_id,
        "status": body.status,
    })
    await db.commit()
    await db.refresh(dos)
    return dos
