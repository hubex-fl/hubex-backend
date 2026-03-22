"""Entity health background worker.

Runs every 30 seconds, updates Entity.health_status and Entity.health_last_seen_at
based on the last_seen_at of its bound, enabled devices.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device
from app.db.models.entities import Entity, EntityDeviceBinding
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")

UPDATE_INTERVAL = 30  # seconds
ONLINE_WINDOW_SECONDS = 30
STALE_WINDOW_SECONDS = 120


def _compute_health(last_seen_values: list[datetime | None], now: datetime) -> tuple[str, datetime | None]:
    """Return (status, most_recent_last_seen_at) from a list of device last_seen_at values."""
    if not last_seen_values:
        return "unknown", None

    worst = "ok"
    most_recent: datetime | None = None

    for lsa in last_seen_values:
        if lsa is None:
            worst = "offline"
            continue
        if lsa.tzinfo is None:
            lsa = lsa.replace(tzinfo=timezone.utc)
        if most_recent is None or lsa > most_recent:
            most_recent = lsa
        age = (now - lsa).total_seconds()
        if age > STALE_WINDOW_SECONDS:
            if worst != "offline":
                worst = "offline"
        elif age > ONLINE_WINDOW_SECONDS:
            if worst == "ok":
                worst = "stale"

    return worst, most_recent


async def run_health_cycle(db: AsyncSession, now: datetime) -> None:
    """Update health_status for all entities."""
    res = await db.execute(select(Entity))
    entities: list[Entity] = list(res.scalars().all())

    for entity in entities:
        res_dev = await db.execute(
            select(Device.last_seen_at)
            .join(EntityDeviceBinding, EntityDeviceBinding.device_id == Device.id)
            .where(
                EntityDeviceBinding.entity_id == entity.entity_id,
                EntityDeviceBinding.enabled.is_(True),
            )
        )
        last_seen_values = list(res_dev.scalars().all())
        status, most_recent = _compute_health(last_seen_values, now)
        entity.health_status = status
        if most_recent is not None:
            entity.health_last_seen_at = most_recent

    await db.commit()


async def health_worker_loop() -> None:
    """Background loop: updates entity health every UPDATE_INTERVAL seconds."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_health_cycle(db, datetime.now(timezone.utc))
        except Exception:
            logger.exception("health_worker: unhandled error in health cycle")
        await asyncio.sleep(UPDATE_INTERVAL)
