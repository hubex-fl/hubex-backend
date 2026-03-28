"""Background task: prune old variable_history entries.

Runs every hour. Deletes entries older than HUBEX_HISTORY_RETENTION_DAYS (default: 30).
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db.models.variables import VariableHistory
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")

RETENTION_INTERVAL = 3600  # run every hour
_RETENTION_DAYS_ENV = "HUBEX_HISTORY_RETENTION_DAYS"
_DEFAULT_RETENTION_DAYS = 30


def _get_retention_days() -> int:
    try:
        return int(os.environ.get(_RETENTION_DAYS_ENV, _DEFAULT_RETENTION_DAYS))
    except (TypeError, ValueError):
        return _DEFAULT_RETENTION_DAYS


async def _prune_once() -> int:
    """Delete entries older than retention window. Returns count deleted."""
    days = _get_retention_days()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(VariableHistory).where(VariableHistory.recorded_at < cutoff)
        )
        await db.commit()
        deleted = result.rowcount
    if deleted:
        logger.info("history_retention: pruned %s entries older than %sd", deleted, days)
    return deleted


async def history_retention_loop() -> None:
    """Long-running background task for history retention pruning."""
    logger.info("history_retention: started (retention=%sd)", _get_retention_days())
    while True:
        try:
            await _prune_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("history_retention: error during prune: %s", exc)
        await asyncio.sleep(RETENTION_INTERVAL)
