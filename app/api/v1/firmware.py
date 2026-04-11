"""Firmware Builder API (Sprint 4 + Sprint 7 OTA integration).

Endpoints:

    POST   /api/v1/firmware/build                      — queue a new build
    GET    /api/v1/firmware/builds                     — list recent builds
    GET    /api/v1/firmware/builds/{build_id}          — single build status
    GET    /api/v1/firmware/builds/{build_id}/logs     — plain-text logs
    GET    /api/v1/firmware/builds/{build_id}/download — .bin download (user auth)
    POST   /api/v1/firmware/builds/{build_id}/cancel   — best-effort cancel
    POST   /api/v1/firmware/builds/{build_id}/ota      — Sprint 7: push build to device
    GET    /api/v1/firmware/builds/{build_id}/ota-artifact — Sprint 7: device-auth fetch

All endpoints are gated by the ``firmware_builder`` feature flag (which
itself requires ``orchestrator`` + ``hardware``) via ``ROUTE_FEATURES``
in ``app/core/features.py``.

Sprint 7 integration with the existing OTA rollout infrastructure
(``app/db/models/ota.py``, ``app/api/v1/ota.py``, ``app/core/ota_worker.py``):

Users pick a successful build + a target device on the Firmware Builder
UI. The ``/ota`` endpoint then creates three rows atomically:

1. ``FirmwareVersion`` — with ``binary_url`` pointing at the new
   ``/ota-artifact`` endpoint below (device-token auth, verified
   against the per-device OTA status)
2. ``OtaRollout`` — single-device rollout with ``strategy="immediate"``
   and ``target_filter={"device_id": X, "build_id": Y}``, immediately
   marked ``status="active"``
3. ``DeviceOtaStatus`` — per-device row with ``status="pending"``

The ``firmware_builds.ota_rollout_id`` column (Sprint 7 migration
``h3c7a4d9e1b2``) is updated so the Firmware Builder UI can poll the
rollout status by joining through this FK.

The device polls ``/ota/check`` (existing endpoint) with its device
token, gets the rollout info + binary_url, fetches the ``.bin`` from
``/ota-artifact`` (which is device-auth'd and verifies the device is
actually targeted by this rollout), flashes it, and calls
``/ota/status/{rollout_id}/ack`` to report status.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_device, get_current_user
from app.core.firmware_builder import run_build_job, pio_env_for_chip
from app.core.portainer_client import PortainerError, get_portainer_client
from app.core.system_events import emit_system_event
from app.db.models.device import Device
from app.db.models.firmware_build import FirmwareBuild
from app.db.models.hardware import BoardProfile
from app.db.models.ota import DeviceOtaStatus, FirmwareVersion, OtaRollout
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/firmware", tags=["Firmware"])


# ── Schemas ────────────────────────────────────────────────────────────────


class BuildRequestIn(BaseModel):
    board_profile_id: int
    device_id: int | None = None


class BuildOut(BaseModel):
    id: int
    status: str
    board_profile_id: int
    device_id: int | None
    pio_env: str
    container_name: str | None
    artifact_size_kb: int | None
    artifact_filename: str | None
    error_code: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None
    has_logs: bool
    # Sprint 7 — OTA linkage
    ota_rollout_id: int | None = None
    ota_status: str | None = None  # pending | active | paused | completed | failed

    @staticmethod
    def from_orm(b: FirmwareBuild, ota_status: str | None = None) -> "BuildOut":
        return BuildOut(
            id=b.id,
            status=b.status,
            board_profile_id=b.board_profile_id,
            device_id=b.device_id,
            pio_env=b.pio_env,
            container_name=b.container_name,
            artifact_size_kb=b.artifact_size_kb,
            artifact_filename=b.artifact_filename,
            error_code=b.error_code,
            created_at=b.created_at.isoformat(),
            started_at=b.started_at.isoformat() if b.started_at else None,
            finished_at=b.finished_at.isoformat() if b.finished_at else None,
            has_logs=bool(b.logs),
            ota_rollout_id=b.ota_rollout_id,
            ota_status=ota_status,
        )


class OtaPushIn(BaseModel):
    device_id: int
    release_notes: str | None = None


class OtaPushOut(BaseModel):
    """Response from POST /firmware/builds/{id}/ota.

    Returns the freshly-created rollout + firmware version ids so the
    UI can link the user directly into the OTA Rollouts page if they
    want to monitor detailed progress.
    """
    rollout_id: int
    firmware_id: int
    device_ota_status_id: int
    version: str
    checksum_sha256: str
    build: BuildOut


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/build", response_model=BuildOut, status_code=202)
async def start_build(
    data: BuildRequestIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Queue a new firmware build.

    Returns 202 Accepted + the build row in ``queued`` state. The actual
    compile happens in an ``asyncio.Task`` that bumps the row through
    ``building`` → ``success`` / ``failed``. Clients should poll
    ``GET /firmware/builds/{id}`` for status.
    """
    board = await db.get(BoardProfile, data.board_profile_id)
    if board is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BOARD_NOT_FOUND",
                "message": f"Board profile {data.board_profile_id} not found",
            },
        )

    build = FirmwareBuild(
        user_id=user.id,
        device_id=data.device_id,
        board_profile_id=data.board_profile_id,
        pio_env=pio_env_for_chip(board.chip),
        status="queued",
    )
    db.add(build)
    await emit_system_event(
        db,
        "firmware.build_queued",
        {
            "board_profile_id": data.board_profile_id,
            "board_name": board.name,
            "user_id": user.id,
        },
    )
    await db.commit()
    await db.refresh(build)

    # Fire-and-forget the worker. The task gets its own DB session inside
    # ``run_build_job`` so the request connection can return immediately.
    asyncio.create_task(run_build_job(build.id))
    logger.info(
        "firmware: queued build %s (board=%s user=%s)",
        build.id, board.name, user.id,
    )
    return BuildOut.from_orm(build)


@router.get("/builds", response_model=list[BuildOut])
async def list_builds(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the user's most recent firmware builds, newest first.

    Sprint 7: left-joins OtaRollout so each build row reports the
    current OTA rollout status (if any).
    """
    stmt = (
        select(FirmwareBuild, OtaRollout.status)
        .outerjoin(OtaRollout, OtaRollout.id == FirmwareBuild.ota_rollout_id)
        .where(FirmwareBuild.user_id == user.id)
        .order_by(FirmwareBuild.id.desc())
        .limit(min(max(limit, 1), 200))
    )
    res = await db.execute(stmt)
    rows = res.all()
    return [BuildOut.from_orm(b, ota_status=ota_status) for (b, ota_status) in rows]


@router.get("/builds/{build_id}", response_model=BuildOut)
async def get_build(
    build_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    build = await _get_build_or_fail(db, build_id, user)
    ota_status: str | None = None
    if build.ota_rollout_id is not None:
        rollout = await db.get(OtaRollout, build.ota_rollout_id)
        if rollout is not None:
            ota_status = rollout.status
    return BuildOut.from_orm(build, ota_status=ota_status)


@router.get("/builds/{build_id}/logs", response_class=PlainTextResponse)
async def get_build_logs(
    build_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the build's captured stdout/stderr as plain text.

    For builds still in-flight, this returns what's been written to the
    DB so far. Frontend polls this endpoint for the live log tail.
    """
    build = await _get_build_or_fail(db, build_id, user)
    return build.logs or ""


@router.get("/builds/{build_id}/download")
async def download_build_artifact(
    build_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download the compiled .bin file. 404 until status=success."""
    build = await _get_build_or_fail(db, build_id, user)
    if build.status != "success" or build.artifact_bytes is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ARTIFACT_NOT_READY",
                "message": f"Build {build_id} has no artifact (status={build.status})",
            },
        )
    return Response(
        content=bytes(build.artifact_bytes),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{build.artifact_filename}"',
        },
    )


@router.post("/builds/{build_id}/ota", response_model=OtaPushOut, status_code=201)
async def push_build_to_ota(
    build_id: int,
    data: OtaPushIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sprint 7 — promote a successful build to an OTA rollout.

    Creates FirmwareVersion + OtaRollout + DeviceOtaStatus atomically.
    The rollout is immediately ``active`` with strategy ``immediate``
    so the next `/ota/check` poll from the target device returns the
    new firmware. ``firmware_builds.ota_rollout_id`` is set so the UI
    can poll status via list_builds.
    """
    build = await _get_build_or_fail(db, build_id, user)
    if build.status != "success" or build.artifact_bytes is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BUILD_NOT_READY",
                "message": f"Build {build_id} is not a successful artifact (status={build.status})",
            },
        )
    if build.ota_rollout_id is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BUILD_ALREADY_PROMOTED",
                "message": f"Build {build_id} is already linked to rollout {build.ota_rollout_id}",
            },
        )

    device = await db.get(Device, data.device_id)
    if device is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "DEVICE_NOT_FOUND", "message": f"Device {data.device_id} not found"},
        )

    # Generate a unique pseudo-semver version from the build id so the
    # FirmwareVersion table's unique constraint on `version` doesn't
    # collide with any other firmware record. Format "0.<build_id>.0"
    # is deterministic and human-readable enough for the Admin UI.
    version_str = f"0.{build.id}.0"
    artifact_bytes = bytes(build.artifact_bytes)
    checksum = hashlib.sha256(artifact_bytes).hexdigest()
    binary_url = f"/api/v1/firmware/builds/{build.id}/ota-artifact"

    fw_version = FirmwareVersion(
        version=version_str,
        binary_url=binary_url,
        checksum_sha256=checksum,
        release_notes=data.release_notes
        or f"HubEx Firmware Builder — build #{build.id} ({build.pio_env})",
        min_hw_version=None,
        org_id=None,
    )
    db.add(fw_version)
    await db.flush()  # need fw_version.id for the rollout

    rollout = OtaRollout(
        firmware_id=fw_version.id,
        name=f"Build #{build.id} → Device {device.device_uid}",
        strategy="immediate",
        # target_filter carries both device_id (matched by ota_worker)
        # and build_id (so future tooling can trace a rollout back to
        # its originating build without joining firmware_builds).
        target_filter={"device_id": device.id, "build_id": build.id},
        status="active",
        progress_percent=0,
        org_id=None,
    )
    db.add(rollout)
    await db.flush()

    dos = DeviceOtaStatus(
        device_id=device.id,
        rollout_id=rollout.id,
        firmware_id=fw_version.id,
        status="pending",
    )
    db.add(dos)

    # Link the build back to the rollout so the list_builds endpoint
    # can report OTA status without an extra round-trip.
    build.ota_rollout_id = rollout.id

    await emit_system_event(
        db,
        "firmware.build_promoted_to_ota",
        {
            "build_id": build.id,
            "device_id": device.id,
            "device_uid": device.device_uid,
            "rollout_id": rollout.id,
            "firmware_id": fw_version.id,
            "version": version_str,
            "user_id": user.id,
        },
    )
    await db.commit()
    await db.refresh(dos)
    await db.refresh(build)

    logger.info(
        "firmware: promoted build %s to OTA rollout %s (device=%s user=%s)",
        build.id, rollout.id, device.id, user.id,
    )
    return OtaPushOut(
        rollout_id=rollout.id,
        firmware_id=fw_version.id,
        device_ota_status_id=dos.id,
        version=version_str,
        checksum_sha256=checksum,
        build=BuildOut.from_orm(build, ota_status=rollout.status),
    )


@router.get("/builds/{build_id}/ota-artifact")
async def get_build_ota_artifact(
    build_id: int,
    device: Device = Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    """Sprint 7 — device-auth endpoint that serves the build .bin.

    Called by the device after `/ota/check` returns a binary_url
    pointing at this endpoint. We verify that the device actually has
    a pending/active DeviceOtaStatus row pointing at a rollout whose
    target_filter.build_id matches this build — otherwise any
    device-token could fetch any build by id.
    """
    build = await db.get(FirmwareBuild, build_id)
    if build is None or build.artifact_bytes is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "ARTIFACT_NOT_FOUND", "message": f"Build {build_id} has no artifact"},
        )

    # The device must have a DeviceOtaStatus row pointing at a rollout
    # whose target_filter.build_id == build_id. One SQL join does it.
    res = await db.execute(
        select(DeviceOtaStatus, OtaRollout)
        .join(OtaRollout, OtaRollout.id == DeviceOtaStatus.rollout_id)
        .where(
            DeviceOtaStatus.device_id == device.id,
            DeviceOtaStatus.status.in_(("pending", "downloading")),
            OtaRollout.id == build.ota_rollout_id,
        )
        .limit(1)
    )
    row = res.first()
    if row is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "NO_ACTIVE_ROLLOUT",
                "message": "Device has no pending OTA rollout for this build",
            },
        )

    return Response(
        content=bytes(build.artifact_bytes),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{build.artifact_filename}"',
            "X-Firmware-Build-Id": str(build.id),
            "X-Firmware-Size-Bytes": str(len(build.artifact_bytes)),
        },
    )


@router.post("/builds/{build_id}/cancel", response_model=BuildOut)
async def cancel_build(
    build_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Best-effort cancel.

    If the build is still ``queued`` it's marked cancelled immediately.
    If it's ``building`` we kill the sidecar container via Portainer
    (the worker will observe the container disappearing and mark the
    build failed with a ``CONTAINER_GONE`` code — we overwrite that to
    ``cancelled`` here).
    """
    build = await _get_build_or_fail(db, build_id, user)
    if build.status not in ("queued", "building"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BUILD_NOT_CANCELLABLE",
                "message": f"Build {build_id} is in status '{build.status}'",
            },
        )

    if build.container_name:
        try:
            await get_portainer_client().remove_container(build.container_name, force=True)
        except PortainerError as exc:
            logger.warning(
                "firmware: cancel for build %s could not remove container: %s",
                build_id, exc.message,
            )

    build.status = "cancelled"
    build.finished_at = datetime.now(timezone.utc)
    await emit_system_event(
        db, "firmware.build_cancelled", {"build_id": build_id, "user_id": user.id}
    )
    await db.commit()
    await db.refresh(build)
    return BuildOut.from_orm(build)


# ── Helpers ────────────────────────────────────────────────────────────────


async def _get_build_or_fail(
    db: AsyncSession, build_id: int, user: User
) -> FirmwareBuild:
    build = await db.get(FirmwareBuild, build_id)
    if build is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "BUILD_NOT_FOUND", "message": f"Build {build_id} not found"},
        )
    if build.user_id is not None and build.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"code": "BUILD_FORBIDDEN", "message": "This build belongs to another user"},
        )
    return build
