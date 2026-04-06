"""Partition management for variable_history and retention cleanup.

Handles:
- Creating monthly partitions for variable_history (if table is partitioned)
- Dropping expired partitions (instant vs slow DELETE)
- Pruning old VariableAudit records
- Pruning old VariableHistory records (fallback if not partitioned)
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

PARTITION_CHECK_INTERVAL = 86400  # 24 hours


async def _ensure_future_partitions(db: AsyncSession) -> None:
    """Create next month's partition if it doesn't exist.

    Only works if variable_history is a partitioned table. If the table
    is regular (not partitioned), this is a no-op.
    """
    try:
        # Check if table is partitioned
        result = await db.execute(text(
            "SELECT pt.relname FROM pg_class c "
            "JOIN pg_inherits i ON i.inhparent = c.oid "
            "JOIN pg_class pt ON pt.oid = i.inhrelid "
            "WHERE c.relname = 'variable_history' LIMIT 1"
        ))
        if not result.scalar_one_or_none():
            return  # Not partitioned — skip

        # Create partition for next month
        now = datetime.now(timezone.utc)
        next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_month = (next_month + timedelta(days=32)).replace(day=1)

        part_name = f"variable_history_{next_month.strftime('%Y_%m')}"
        start_str = next_month.strftime("%Y-%m-%d")
        end_str = end_month.strftime("%Y-%m-%d")

        await db.execute(text(
            f"CREATE TABLE IF NOT EXISTS {part_name} "
            f"PARTITION OF variable_history "
            f"FOR VALUES FROM ('{start_str}') TO ('{end_str}')"
        ))
        await db.commit()
        logger.info("partition_manager: ensured partition %s", part_name)

    except Exception as exc:
        logger.debug("partition_manager: partition check skipped (%s)", exc)
        await db.rollback()


async def _drop_expired_partitions(db: AsyncSession) -> None:
    """Drop partitions older than retention period.

    Much faster than DELETE — instant metadata operation.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.history_retention_days)
        cutoff_month = cutoff.replace(day=1)

        # Find child tables of variable_history
        result = await db.execute(text(
            "SELECT pt.relname FROM pg_class c "
            "JOIN pg_inherits i ON i.inhparent = c.oid "
            "JOIN pg_class pt ON pt.oid = i.inhrelid "
            "WHERE c.relname = 'variable_history' "
            "ORDER BY pt.relname"
        ))
        partitions = [row[0] for row in result.fetchall()]

        for part_name in partitions:
            # Parse partition date from name (format: variable_history_YYYY_MM)
            try:
                parts = part_name.replace("variable_history_", "").split("_")
                part_date = datetime(int(parts[0]), int(parts[1]), 1, tzinfo=timezone.utc)
                if part_date < cutoff_month:
                    await db.execute(text(f"DROP TABLE IF EXISTS {part_name}"))
                    await db.commit()
                    logger.info("partition_manager: dropped expired partition %s", part_name)
            except (ValueError, IndexError):
                continue

    except Exception as exc:
        logger.debug("partition_manager: drop partitions skipped (%s)", exc)
        await db.rollback()


async def _prune_variable_history(db: AsyncSession) -> None:
    """Delete old variable_history records (fallback for non-partitioned tables)."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.history_retention_days)
        result = await db.execute(text(
            "DELETE FROM variable_history WHERE recorded_at < :cutoff"
        ), {"cutoff": cutoff})
        count = result.rowcount
        await db.commit()
        if count:
            logger.info("partition_manager: pruned %d old history records", count)
    except Exception as exc:
        logger.warning("partition_manager: history prune failed: %s", exc)
        await db.rollback()


async def _prune_variable_audit(db: AsyncSession) -> None:
    """Delete old variable_audit records beyond retention period."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
        result = await db.execute(text(
            "DELETE FROM variable_audit WHERE created_at < :cutoff"
        ), {"cutoff": cutoff})
        count = result.rowcount
        await db.commit()
        if count:
            logger.info("partition_manager: pruned %d old audit records", count)
    except Exception as exc:
        logger.warning("partition_manager: audit prune failed: %s", exc)
        await db.rollback()


async def partition_maintenance_loop() -> None:
    """Background loop for partition management and retention cleanup.

    Runs every 24 hours.
    """
    from app.db.session import async_session_factory

    logger.info("partition_manager: started (history=%dd, audit=%dd)",
                settings.history_retention_days, settings.audit_retention_days)

    while True:
        try:
            await asyncio.sleep(PARTITION_CHECK_INTERVAL)

            async with async_session_factory() as db:
                await _ensure_future_partitions(db)
                await _drop_expired_partitions(db)
                await _prune_variable_history(db)
                await _prune_variable_audit(db)

        except asyncio.CancelledError:
            logger.info("partition_manager: shutting down")
            break
        except Exception as exc:
            logger.error("partition_manager: unexpected error: %s", exc)
            await asyncio.sleep(60)
