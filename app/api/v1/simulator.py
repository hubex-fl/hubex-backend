"""Simulator API — create, manage, start/stop device simulators."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_current_org_id
from app.db.models.device import Device
from app.db.models.simulator import SimulatorConfig
from app.db.models.user import User
from app.db.models.variables import VariableDefinition
from app.schemas.simulator import (
    SimulatorCreate,
    SimulatorUpdate,
    SimulatorOut,
    SimulatorQuickPulse,
    TemplateInfo,
    VariablePattern,
)
from app.core import simulator_worker

router = APIRouter(prefix="/simulator", tags=["simulator"])


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, TemplateInfo] = {
    "temperature": TemplateInfo(
        key="temperature",
        name="Temperature Sensor",
        description="Temperature, humidity, and pressure sensor with daily cycles",
        variable_patterns=[
            VariablePattern(
                variable_key="temperature",
                pattern="sine",
                config={"min": 18.0, "max": 28.0, "period_seconds": 86400},
            ),
            VariablePattern(
                variable_key="humidity",
                pattern="sine",
                config={"min": 40.0, "max": 70.0, "period_seconds": 86400, "phase_offset": 3.14159},
            ),
            VariablePattern(
                variable_key="pressure",
                pattern="noise",
                config={"center": 1013.0, "amplitude": 5.0},
            ),
        ],
    ),
    "energy": TemplateInfo(
        key="energy",
        name="Energy Meter",
        description="Power consumption, cumulative energy, and voltage readings",
        variable_patterns=[
            VariablePattern(
                variable_key="power_watts",
                pattern="sine",
                config={"min": 200.0, "max": 2000.0, "period_seconds": 86400},
            ),
            VariablePattern(
                variable_key="energy_kwh",
                pattern="counter",
                config={"start": 0.0, "increment": 0.5, "interval_seconds": 60},
            ),
            VariablePattern(
                variable_key="voltage",
                pattern="noise",
                config={"center": 230.0, "amplitude": 2.0},
            ),
        ],
    ),
    "gps": TemplateInfo(
        key="gps",
        name="GPS Tracker",
        description="Moving GPS position with speed and battery drain",
        variable_patterns=[
            VariablePattern(
                variable_key="position",
                pattern="gps_track",
                config={
                    "waypoints": [
                        {"lat": 52.5200, "lng": 13.4050},
                        {"lat": 52.5230, "lng": 13.4100},
                        {"lat": 52.5260, "lng": 13.4000},
                        {"lat": 52.5220, "lng": 13.3950},
                        {"lat": 52.5200, "lng": 13.4050},
                    ],
                    "speed_kmh": 30.0,
                },
            ),
            VariablePattern(
                variable_key="speed",
                pattern="noise",
                config={"center": 30.0, "amplitude": 10.0},
            ),
            VariablePattern(
                variable_key="battery",
                pattern="ramp",
                config={"start": 100.0, "end": 0.0, "duration_seconds": 28800, "loop": True},
            ),
        ],
    ),
    "motion": TemplateInfo(
        key="motion",
        name="Motion Sensor",
        description="Motion detection with ambient light levels",
        variable_patterns=[
            VariablePattern(
                variable_key="motion",
                pattern="step",
                config={"values": [False, False, False, True, False, True], "interval_seconds": 30},
            ),
            VariablePattern(
                variable_key="luminance",
                pattern="sine",
                config={"min": 0.0, "max": 1000.0, "period_seconds": 86400},
            ),
        ],
    ),
    "weather": TemplateInfo(
        key="weather",
        name="Weather Station",
        description="Full weather station with temperature, humidity, wind, and rain",
        variable_patterns=[
            VariablePattern(
                variable_key="temperature",
                pattern="sine",
                config={"min": 5.0, "max": 25.0, "period_seconds": 86400},
            ),
            VariablePattern(
                variable_key="humidity",
                pattern="sine",
                config={"min": 30.0, "max": 90.0, "period_seconds": 86400, "phase_offset": 3.14159},
            ),
            VariablePattern(
                variable_key="wind_speed",
                pattern="random_walk",
                config={"center": 10.0, "volatility": 2.0, "min_bound": 0.0, "max_bound": 50.0},
            ),
            VariablePattern(
                variable_key="rain_mm",
                pattern="counter",
                config={"start": 0.0, "increment": 0.2, "interval_seconds": 300, "reset_at": 50.0},
            ),
        ],
    ),
    # Sprint 8 R4 Bucket C F19: new simulator templates that line up with
    # the expanded Sprint 5b component catalog (BME280, BH1750, HC-SR04,
    # servo, LED PWM, door contact). These round out the "hardware demo"
    # story so the Sandbox looks alive after a fresh register.
    "bme280": TemplateInfo(
        key="bme280",
        name="BME280 Environmental",
        description="BME280 I2C sensor — temperature, humidity, pressure, and gas resistance (IAQ)",
        variable_patterns=[
            VariablePattern(
                variable_key="temperature",
                pattern="sine",
                config={"min": 19.0, "max": 24.5, "period_seconds": 86400},
            ),
            VariablePattern(
                variable_key="humidity",
                pattern="sine",
                config={"min": 42.0, "max": 58.0, "period_seconds": 86400, "phase_offset": 3.14159},
            ),
            VariablePattern(
                variable_key="pressure",
                pattern="noise",
                config={"center": 1013.25, "amplitude": 3.5},
            ),
            VariablePattern(
                variable_key="gas_resistance_kohm",
                pattern="random_walk",
                config={"center": 150.0, "volatility": 12.0, "min_bound": 50.0, "max_bound": 400.0},
            ),
        ],
    ),
    "bh1750": TemplateInfo(
        key="bh1750",
        name="BH1750 Light Sensor",
        description="BH1750 ambient light meter — day/night lux cycle with curtain noise",
        variable_patterns=[
            VariablePattern(
                variable_key="lux",
                pattern="sine",
                config={"min": 0.0, "max": 1200.0, "period_seconds": 86400},
            ),
        ],
    ),
    "ultrasonic": TemplateInfo(
        key="ultrasonic",
        name="HC-SR04 Distance",
        description="HC-SR04 ultrasonic distance sensor — ping-pong distance with presence spikes",
        variable_patterns=[
            VariablePattern(
                variable_key="distance_cm",
                pattern="random_walk",
                config={"center": 85.0, "volatility": 18.0, "min_bound": 4.0, "max_bound": 200.0},
            ),
            VariablePattern(
                variable_key="object_detected",
                pattern="step",
                config={"values": [False, False, True, False, False, False, True, False], "interval_seconds": 15},
            ),
        ],
    ),
    "servo": TemplateInfo(
        key="servo",
        name="Servo Motor",
        description="Servo actuator — angle sweeps between two set-points on schedule",
        variable_patterns=[
            VariablePattern(
                variable_key="angle_deg",
                pattern="sine",
                config={"min": 0.0, "max": 180.0, "period_seconds": 120},
            ),
            VariablePattern(
                variable_key="target_angle_deg",
                pattern="step",
                config={"values": [0, 45, 90, 135, 180, 135, 90, 45], "interval_seconds": 15},
            ),
        ],
    ),
    "led_pwm": TemplateInfo(
        key="led_pwm",
        name="LED Dimmer (PWM)",
        description="PWM LED channel — brightness ramps up and fades through the day",
        variable_patterns=[
            VariablePattern(
                variable_key="brightness_pct",
                pattern="sine",
                config={"min": 0.0, "max": 100.0, "period_seconds": 300},
            ),
            VariablePattern(
                variable_key="duty_cycle",
                pattern="ramp",
                config={"start": 0.0, "end": 255.0, "duration_seconds": 600, "loop": True},
            ),
        ],
    ),
    "door_contact": TemplateInfo(
        key="door_contact",
        name="Door/Window Contact",
        description="Reed-switch contact sensor — open/closed events with battery drain",
        variable_patterns=[
            VariablePattern(
                variable_key="contact_closed",
                pattern="step",
                config={"values": [True, True, True, False, True, True, False, True], "interval_seconds": 45},
            ),
            VariablePattern(
                variable_key="battery_pct",
                pattern="ramp",
                config={"start": 100.0, "end": 0.0, "duration_seconds": 86400 * 30, "loop": True},
            ),
        ],
    ),
    "custom": TemplateInfo(
        key="custom",
        name="Custom",
        description="Empty template — define your own variables and patterns",
        variable_patterns=[],
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sim_to_out(sim: SimulatorConfig) -> SimulatorOut:
    patterns = sim.variable_patterns or []
    parsed_patterns = []
    for p in patterns:
        try:
            parsed_patterns.append(VariablePattern(**p))
        except Exception:
            parsed_patterns.append(
                VariablePattern(variable_key=p.get("variable_key", "?"), pattern="noise", config={})
            )

    return SimulatorOut(
        id=sim.id,
        org_id=sim.org_id,
        owner_id=sim.owner_id,
        device_id=sim.device_id,
        device_uid=sim.device_uid,
        name=sim.name,
        description=sim.description,
        template=sim.template,
        variable_patterns=parsed_patterns,
        interval_seconds=sim.interval_seconds,
        speed_multiplier=sim.speed_multiplier,
        is_active=sim.is_active,
        is_virtual_device=sim.is_virtual_device,
        total_points_sent=sim.total_points_sent,
        started_at=sim.started_at,
        last_value_at=sim.last_value_at,
        created_at=sim.created_at,
        updated_at=sim.updated_at,
    )


async def _get_sim_or_404(
    db: AsyncSession, sim_id: int, owner_id: int
) -> SimulatorConfig:
    res = await db.execute(
        select(SimulatorConfig).where(
            SimulatorConfig.id == sim_id,
            SimulatorConfig.owner_id == owner_id,
        )
    )
    sim = res.scalar_one_or_none()
    if sim is None:
        raise HTTPException(status_code=404, detail="simulator not found")
    return sim


async def _create_virtual_device(
    db: AsyncSession,
    user: User,
    org_id: int | None,
    sim_name: str,
    variable_patterns: list[VariablePattern],
) -> Device:
    """Create a virtual device and its variable definitions."""
    uid = f"sim-{sim_name.lower().replace(' ', '-')[:30]}-{secrets.token_hex(4)}"
    device = Device(
        device_uid=uid,
        name=f"[SIM] {sim_name}",
        device_type="simulator",
        category="hardware",
        owner_user_id=user.id,
        org_id=org_id,
        is_claimed=True,
        capabilities={"simulated": True},
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(device)
    await db.flush()

    # Create variable definitions for the patterns
    for pat in variable_patterns:
        # Check if definition already exists
        existing = await db.execute(
            select(VariableDefinition).where(VariableDefinition.key == pat.variable_key)
        )
        if existing.scalar_one_or_none() is None:
            vtype = "float"
            if pat.pattern == "gps_track":
                vtype = "json"
            elif pat.pattern == "step":
                vals = pat.config.get("values", [])
                if vals and isinstance(vals[0], bool):
                    vtype = "bool"
            db.add(VariableDefinition(
                key=pat.variable_key,
                scope="device",
                value_type=vtype,
                description=f"Simulated: {pat.variable_key}",
                device_writable=True,
            ))

    await db.flush()
    return device


# ---------------------------------------------------------------------------
# Templates endpoint
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=list[TemplateInfo])
async def list_templates(
    _user: User = Depends(get_current_user),
):
    """List available simulator templates with predefined variable patterns."""
    return list(_TEMPLATES.values())


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.get("/configs", response_model=list[SimulatorOut])
async def list_simulators(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all simulators owned by the current user."""
    res = await db.execute(
        select(SimulatorConfig)
        .where(SimulatorConfig.owner_id == user.id)
        .order_by(SimulatorConfig.id)
    )
    sims = res.scalars().all()
    return [_sim_to_out(s) for s in sims]


@router.post("/configs", response_model=SimulatorOut, status_code=201)
async def create_simulator(
    body: SimulatorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    """Create a new simulator configuration.

    If is_virtual_device is true, a virtual device is created automatically.
    If device_uid is provided and is_virtual_device is false, the simulator attaches
    to the existing device.
    If a template is specified, its variable_patterns are used as defaults (unless
    the caller provides their own).
    """
    # Apply template patterns if none provided
    patterns = body.variable_patterns
    if not patterns and body.template and body.template in _TEMPLATES:
        patterns = _TEMPLATES[body.template].variable_patterns

    device_id: int | None = None
    device_uid: str | None = body.device_uid

    if body.is_virtual_device:
        device = await _create_virtual_device(db, user, org_id, body.name, patterns)
        device_id = device.id
        device_uid = device.device_uid
    elif body.device_uid:
        # Attach to existing device
        res = await db.execute(
            select(Device).where(
                Device.device_uid == body.device_uid,
                Device.owner_user_id == user.id,
            )
        )
        existing = res.scalar_one_or_none()
        if existing is None:
            raise HTTPException(status_code=404, detail="device not found")
        device_id = existing.id
        device_uid = existing.device_uid

    sim = SimulatorConfig(
        org_id=org_id,
        owner_id=user.id,
        device_id=device_id,
        device_uid=device_uid,
        name=body.name,
        description=body.description,
        template=body.template,
        variable_patterns=[p.model_dump() for p in patterns],
        interval_seconds=body.interval_seconds,
        speed_multiplier=body.speed_multiplier,
        is_virtual_device=body.is_virtual_device,
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)
    return _sim_to_out(sim)


@router.get("/configs/{sim_id}", response_model=SimulatorOut)
async def get_simulator(
    sim_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a simulator configuration with current stats."""
    sim = await _get_sim_or_404(db, sim_id, user.id)
    # Sync is_active with worker state
    running = simulator_worker.is_running(sim.id)
    if sim.is_active != running:
        sim.is_active = running
        await db.commit()
        await db.refresh(sim)
    return _sim_to_out(sim)


@router.put("/configs/{sim_id}", response_model=SimulatorOut)
async def update_simulator(
    sim_id: int,
    body: SimulatorUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a simulator configuration. Stops the simulator if it's running."""
    sim = await _get_sim_or_404(db, sim_id, user.id)

    # Stop if running (config changed)
    if sim.is_active:
        simulator_worker.stop_simulator(sim.id)
        sim.is_active = False

    if body.name is not None:
        sim.name = body.name
    if body.description is not None:
        sim.description = body.description
    if body.variable_patterns is not None:
        sim.variable_patterns = [p.model_dump() for p in body.variable_patterns]
    if body.interval_seconds is not None:
        sim.interval_seconds = body.interval_seconds
    if body.speed_multiplier is not None:
        sim.speed_multiplier = body.speed_multiplier

    await db.commit()
    await db.refresh(sim)
    return _sim_to_out(sim)


@router.delete("/configs/{sim_id}", status_code=204)
async def delete_simulator(
    sim_id: int,
    delete_device: bool = Query(False, description="Also delete the virtual device"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a simulator. Optionally deletes the associated virtual device."""
    sim = await _get_sim_or_404(db, sim_id, user.id)

    # Stop if running
    if sim.is_active:
        simulator_worker.stop_simulator(sim.id)

    virtual_device_id = sim.device_id if sim.is_virtual_device else None

    await db.execute(
        delete(SimulatorConfig).where(SimulatorConfig.id == sim.id)
    )

    # Optionally delete the virtual device
    if delete_device and virtual_device_id:
        await db.execute(
            delete(Device).where(Device.id == virtual_device_id)
        )

    await db.commit()


# ---------------------------------------------------------------------------
# Start / Stop / Pulse
# ---------------------------------------------------------------------------


@router.post("/configs/{sim_id}/start", response_model=SimulatorOut)
async def start_simulator(
    sim_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a simulator. Begins generating data in the background."""
    sim = await _get_sim_or_404(db, sim_id, user.id)

    if not sim.device_id or not sim.device_uid:
        raise HTTPException(status_code=400, detail="simulator has no device linked")

    if sim.is_active and simulator_worker.is_running(sim.id):
        return _sim_to_out(sim)  # Already running

    sim.is_active = True
    sim.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sim)

    simulator_worker.start_simulator(sim.id)
    return _sim_to_out(sim)


@router.post("/configs/{sim_id}/stop", response_model=SimulatorOut)
async def stop_simulator(
    sim_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stop a running simulator."""
    sim = await _get_sim_or_404(db, sim_id, user.id)

    simulator_worker.stop_simulator(sim.id)
    sim.is_active = False
    await db.commit()
    await db.refresh(sim)
    return _sim_to_out(sim)


@router.post("/configs/{sim_id}/pulse", response_model=dict)
async def pulse_single_value(
    sim_id: int,
    body: SimulatorQuickPulse,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a single value for one variable on the simulator's device."""
    sim = await _get_sim_or_404(db, sim_id, user.id)

    if not sim.device_id or not sim.device_uid:
        raise HTTPException(status_code=400, detail="simulator has no device linked")

    from app.api.v1.telemetry import _bridge_telemetry_to_variables

    await _bridge_telemetry_to_variables(
        device_id=sim.device_id,
        device_uid=sim.device_uid,
        event_type="simulator",
        payload={body.variable_key: body.value},
    )

    return {"ok": True, "variable_key": body.variable_key, "value": body.value}


# ---------------------------------------------------------------------------
# Quick Pulse (device-centric, no simulator required)
# ---------------------------------------------------------------------------


@router.post("/quick-pulse", response_model=dict)
async def quick_pulse(
    body: SimulatorQuickPulse,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Push a single value for any variable on any device owned by the user.

    Useful from Device Detail page to quickly inject test data without
    creating a full simulator configuration.
    """
    res = await db.execute(
        select(Device).where(
            Device.device_uid == body.device_uid,
            Device.owner_user_id == user.id,
        )
    )
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="device not found")

    from app.api.v1.telemetry import _bridge_telemetry_to_variables

    await _bridge_telemetry_to_variables(
        device_id=device.id,
        device_uid=device.device_uid,
        event_type="simulator",
        payload={body.variable_key: body.value},
    )

    # Update device last_seen
    device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True, "device_uid": body.device_uid, "variable_key": body.variable_key, "value": body.value}
