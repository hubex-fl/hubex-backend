"""OTA rollout background worker.

Runs every 60 s. For each active rollout:
- Computes target devices from target_filter.
- Assigns the next batch (10% for staged, 5% for canary, 100% for immediate).
- Updates progress_percent.
- Marks rollout completed when all devices finish.

target_filter formats
---------------------
{"all": true}                 — all devices (org-scoped when rollout.org_id set)
{"device_ids": [1, 2, 3]}    — explicit list
{"entity_id": "<uuid>"}       — devices bound to entity
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system_events import emit_system_event
from app.db.models.device import Device
from app.db.models.entities import EntityDeviceBinding
from app.db.models.ota import DeviceOtaStatus, OtaRollout
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")

WORKER_INTERVAL = 60  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_target_device_ids(db: AsyncSession, rollout: OtaRollout) -> list[int]:
    target_filter = rollout.target_filter or {}

    if target_filter.get("all"):
        stmt = select(Device.id)
        if rollout.org_id is not None:
            stmt = stmt.where(Device.org_id == rollout.org_id)
        res = await db.execute(stmt)
        return [row[0] for row in res.all()]

    if "device_ids" in target_filter:
        return [int(x) for x in target_filter["device_ids"]]

    if "entity_id" in target_filter:
        res = await db.execute(
            select(EntityDeviceBinding.device_id).where(
                EntityDeviceBinding.entity_id == str(target_filter["entity_id"]),
                EntityDeviceBinding.enabled.is_(True),
            )
        )
        return [row[0] for row in res.all()]

    return []


async def _process_rollout(db: AsyncSession, rollout: OtaRollout) -> None:
    all_device_ids = await _get_target_device_ids(db, rollout)
    total = len(all_device_ids)

    if total == 0:
        rollout.status = "completed"
        rollout.progress_percent = 100
        await emit_system_event(db, "ota.rollout.completed", {
            "rollout_id": rollout.id, "name": rollout.name,
        })
        return

    # Assigned so far
    res = await db.execute(
        select(DeviceOtaStatus.device_id).where(DeviceOtaStatus.rollout_id == rollout.id)
    )
    assigned_ids = {row[0] for row in res.all()}

    # Terminal count (done / failed / skipped)
    res = await db.execute(
        select(func.count()).select_from(DeviceOtaStatus).where(
            DeviceOtaStatus.rollout_id == rollout.id,
            DeviceOtaStatus.status.in_(["done", "failed", "skipped"]),
        )
    )
    terminal_count = res.scalar_one()
    assigned_count = len(assigned_ids)

    # Update progress
    if assigned_count > 0:
        rollout.progress_percent = min(99, int(terminal_count / total * 100))

    # All done?
    if assigned_count == total and terminal_count == total:
        rollout.status = "completed"
        rollout.progress_percent = 100
        await emit_system_event(db, "ota.rollout.completed", {
            "rollout_id": rollout.id, "name": rollout.name,
        })
        return

    unassigned = [d for d in all_device_ids if d not in assigned_ids]
    if not unassigned:
        return  # All assigned — waiting for devices to finish

    # Only expand when no in-progress devices remain (or initial assignment)
    if assigned_count > 0:
        res = await db.execute(
            select(func.count()).select_from(DeviceOtaStatus).where(
                DeviceOtaStatus.rollout_id == rollout.id,
                DeviceOtaStatus.status.notin_(["done", "failed", "skipped"]),
            )
        )
        in_progress = res.scalar_one()
        if in_progress > 0:
            return

    # Batch size per strategy
    if rollout.strategy == "immediate":
        batch_size = len(unassigned)
    elif rollout.strategy == "canary":
        batch_size = max(1, total // 20)  # ~5 %
    else:  # staged
        batch_size = max(1, total // 10)  # ~10 %

    for device_id in unassigned[:batch_size]:
        db.add(DeviceOtaStatus(
            device_id=device_id,
            rollout_id=rollout.id,
            firmware_id=rollout.firmware_id,
            status="pending",
        ))


# ---------------------------------------------------------------------------
# Core cycle (testable)
# ---------------------------------------------------------------------------

async def run_ota_cycle(db: AsyncSession) -> None:
    res = await db.execute(
        select(OtaRollout).where(OtaRollout.status == "active")
    )
    rollouts = list(res.scalars().all())

    for rollout in rollouts:
        try:
            await _process_rollout(db, rollout)
        except Exception:
            logger.exception("ota_worker: error processing rollout_id=%d", rollout.id)

    await db.commit()


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------

async def ota_worker_loop() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_ota_cycle(db)
        except Exception:
            logger.exception("ota_worker: unhandled error")
        await asyncio.sleep(WORKER_INTERVAL)
