"""
Background worker that drives all active simulators.

On startup, loads active SimulatorConfigs from DB and runs periodic loops
that generate values and write them through the telemetry variable bridge.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.simulator_engine import generate_value
from app.db.models.simulator import SimulatorConfig
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")

# Global registry: simulator_id -> asyncio.Task
_running_tasks: dict[int, asyncio.Task] = {}

# Last values per simulator per variable_key (for random_walk, manual, etc.)
_last_values: dict[int, dict[str, Any]] = {}

# Flag to signal global shutdown
_shutdown_event: asyncio.Event | None = None


async def _write_simulator_values(
    device_id: int,
    device_uid: str,
    values: dict[str, Any],
) -> None:
    """Write generated values through the telemetry-to-variables bridge."""
    from app.api.v1.telemetry import _bridge_telemetry_to_variables

    await _bridge_telemetry_to_variables(
        device_id=device_id,
        device_uid=device_uid,
        event_type="simulator",
        payload=values,
    )


async def _update_device_last_seen(device_id: int) -> None:
    """Mark the simulated device as recently seen."""
    try:
        async with AsyncSessionLocal() as db:
            from app.db.models.device import Device

            await db.execute(
                update(Device)
                .where(Device.id == device_id)
                .values(last_seen_at=datetime.now(timezone.utc))
            )
            await db.commit()
    except Exception:
        pass


async def _run_single_simulator(sim_id: int) -> None:
    """Run one simulator in a loop until cancelled or deactivated."""
    logger.info("simulator_worker: starting simulator id=%d", sim_id)
    _last_values.setdefault(sim_id, {})

    try:
        # Load config
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(SimulatorConfig).where(SimulatorConfig.id == sim_id)
            )
            sim = res.scalar_one_or_none()
            if not sim or not sim.is_active:
                return

            device_id = sim.device_id
            device_uid = sim.device_uid
            patterns = sim.variable_patterns or []
            interval = max(sim.interval_seconds, 1)
            speed = max(sim.speed_multiplier, 0.1)
            started_at = sim.started_at or datetime.now(timezone.utc)

        if not device_id or not device_uid:
            logger.warning("simulator_worker: sim %d has no device linked", sim_id)
            return

        while True:
            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds() * speed
            values: dict[str, Any] = {}

            for pat_cfg in patterns:
                var_key = pat_cfg.get("variable_key", "")
                pattern_type = pat_cfg.get("pattern", "noise")
                config = pat_cfg.get("config", {})
                last = _last_values[sim_id].get(var_key)

                try:
                    val = generate_value(pattern_type, config, elapsed, last)
                    values[var_key] = val
                    _last_values[sim_id][var_key] = val
                except Exception as exc:
                    logger.debug(
                        "simulator_worker: error generating %s for sim %d: %s",
                        var_key, sim_id, exc,
                    )

            if values:
                try:
                    await _write_simulator_values(device_id, device_uid, values)
                    await _update_device_last_seen(device_id)
                except Exception as exc:
                    logger.debug("simulator_worker: write error sim %d: %s", sim_id, exc)

                # Update stats
                try:
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(SimulatorConfig)
                            .where(SimulatorConfig.id == sim_id)
                            .values(
                                total_points_sent=SimulatorConfig.total_points_sent + len(values),
                                last_value_at=datetime.now(timezone.utc),
                            )
                        )
                        await db.commit()
                except Exception:
                    pass

            # Sleep for the configured interval (adjusted by speed multiplier)
            sleep_time = interval / speed
            sleep_time = max(0.1, min(sleep_time, 3600))
            await asyncio.sleep(sleep_time)

            # Reload config in case it was updated
            try:
                async with AsyncSessionLocal() as db:
                    res = await db.execute(
                        select(SimulatorConfig).where(SimulatorConfig.id == sim_id)
                    )
                    sim = res.scalar_one_or_none()
                    if not sim or not sim.is_active:
                        logger.info("simulator_worker: sim %d deactivated, stopping", sim_id)
                        return

                    patterns = sim.variable_patterns or []
                    interval = max(sim.interval_seconds, 1)
                    speed = max(sim.speed_multiplier, 0.1)
            except Exception:
                pass

    except asyncio.CancelledError:
        logger.info("simulator_worker: sim %d cancelled", sim_id)
    except Exception as exc:
        logger.warning("simulator_worker: sim %d unexpected error: %s", sim_id, exc)
    finally:
        _running_tasks.pop(sim_id, None)
        _last_values.pop(sim_id, None)


def start_simulator(sim_id: int) -> None:
    """Start a simulator by creating an asyncio task for it."""
    if sim_id in _running_tasks:
        task = _running_tasks[sim_id]
        if not task.done():
            return  # Already running
    task = asyncio.create_task(_run_single_simulator(sim_id))
    _running_tasks[sim_id] = task


def stop_simulator(sim_id: int) -> None:
    """Stop a running simulator task."""
    task = _running_tasks.get(sim_id)
    if task and not task.done():
        task.cancel()
    _running_tasks.pop(sim_id, None)
    _last_values.pop(sim_id, None)


def is_running(sim_id: int) -> bool:
    """Check if a simulator is currently running."""
    task = _running_tasks.get(sim_id)
    return task is not None and not task.done()


async def load_active_simulators() -> int:
    """Load and start all active simulators from the database. Returns count started."""
    count = 0
    try:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(SimulatorConfig).where(SimulatorConfig.is_active.is_(True))
            )
            active_sims = res.scalars().all()
            for sim in active_sims:
                start_simulator(sim.id)
                count += 1
    except Exception as exc:
        logger.warning("simulator_worker: failed to load active simulators: %s", exc)
    if count:
        logger.info("simulator_worker: loaded %d active simulators", count)
    return count


async def shutdown_all() -> None:
    """Gracefully shut down all running simulator tasks."""
    for sim_id in list(_running_tasks.keys()):
        stop_simulator(sim_id)
    # Wait for all tasks to finish
    tasks = list(_running_tasks.values())
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _running_tasks.clear()
    _last_values.clear()
    logger.info("simulator_worker: all simulators stopped")


async def simulator_worker_loop() -> None:
    """Main entry point called from app lifespan. Loads active sims then waits for shutdown."""
    await load_active_simulators()
    try:
        # Keep the loop alive so the task doesn't complete
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await shutdown_all()
