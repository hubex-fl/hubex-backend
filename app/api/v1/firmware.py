"""Firmware Builder API (Sprint 4).

Endpoints:

    POST   /api/v1/firmware/build                   — queue a new build
    GET    /api/v1/firmware/builds                  — list recent builds
    GET    /api/v1/firmware/builds/{build_id}       — single build status
    GET    /api/v1/firmware/builds/{build_id}/logs  — plain-text logs
    GET    /api/v1/firmware/builds/{build_id}/download — .bin download
    POST   /api/v1/firmware/builds/{build_id}/cancel — best-effort cancel

All endpoints are gated by the ``firmware_builder`` feature flag (which
itself requires ``orchestrator`` + ``hardware``) via ``ROUTE_FEATURES``
in ``app/core/features.py``.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.core.firmware_builder import run_build_job, pio_env_for_chip
from app.core.portainer_client import PortainerError, get_portainer_client
from app.core.system_events import emit_system_event
from app.db.models.firmware_build import FirmwareBuild
from app.db.models.hardware import BoardProfile
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

    @staticmethod
    def from_orm(b: FirmwareBuild) -> "BuildOut":
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
        )


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
    """Return the user's most recent firmware builds, newest first."""
    stmt = (
        select(FirmwareBuild)
        .where(FirmwareBuild.user_id == user.id)
        .order_by(FirmwareBuild.id.desc())
        .limit(min(max(limit, 1), 200))
    )
    res = await db.execute(stmt)
    return [BuildOut.from_orm(b) for b in res.scalars().all()]


@router.get("/builds/{build_id}", response_model=BuildOut)
async def get_build(
    build_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    build = await _get_build_or_fail(db, build_id, user)
    return BuildOut.from_orm(build)


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
