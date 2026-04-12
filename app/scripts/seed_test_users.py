"""Sprint 9 — Seed test-user accounts with the 'tester' role + demo simulators.

Creates (or updates) test accounts on the hubextest.tech demo instance.
Each test user gets the 'tester' RBAC role which gives them interactive
access to devices, variables, dashboards, automations, and simulators
but NOT to config, org admin, CMS publish, webhooks, OTA, or API keys.

Also creates and starts 2-3 simulators so the test user has live data
from the moment they log in — variables accumulate, dashboards have
something to show, events fire.

Run manually:
    python -m app.scripts.seed_test_users

Or add to the daily-reset cron on the VPS so test users survive resets.

Environment variables (all optional):
    HUBEX_TEST_EMAILS   — comma-separated emails (default: test@hubextest.tech)
    HUBEX_TEST_PASSWORD — shared password (default: HubExDemo2025!)
    HUBEX_TEST_ORG_ID   — org to assign tester role in (default: 1)
"""

import asyncio
import logging
import os
import secrets

from datetime import datetime, timezone
from sqlalchemy import select

from app.core.capabilities import ROLE_CAPS, resolve_caps_for_role
from app.core.security import hash_password, verify_password
from app.db.models.device import Device
from app.db.models.orgs import OrganizationUser
from app.db.models.simulator import SimulatorConfig
from app.db.models.user import User
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")


DEFAULT_EMAILS = "test@hubextest.tech"
DEFAULT_PASSWORD = "HubExDemo2025!"
DEFAULT_ORG_ID = 1


async def seed_test_user(
    db,
    *,
    email: str,
    password: str,
    org_id: int,
) -> str:
    """Create or update a single test user with the 'tester' role.

    Returns a status string for logging.
    """
    # 1. Upsert user record
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()

    tester_caps = resolve_caps_for_role("tester")

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            caps=tester_caps,
        )
        db.add(user)
        await db.flush()
        status = "created"
    else:
        # Ensure password + caps match
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
        user.caps = tester_caps
        status = "updated"

    # 2. Ensure OrganizationUser membership with role='tester'
    ou_res = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == user.id,
        )
    )
    ou = ou_res.scalar_one_or_none()
    if ou is None:
        ou = OrganizationUser(org_id=org_id, user_id=user.id, role="tester")
        db.add(ou)
        status += "+joined-org"
    elif ou.role != "tester":
        ou.role = "tester"
        status += "+role-fixed"

    await db.commit()
    return status


# ── Simulator Seeding ────────────────────────────────────────────────────────

# Templates to auto-create for the test user. These match the backend
# _TEMPLATES in app/api/v1/simulator.py so they produce realistic data.
SEED_SIMULATORS = [
    {
        "name": "[Demo] Temperature Sensor",
        "template": "temperature",
        "description": "Auto-created demo simulator — temperature, humidity, pressure",
        "interval_seconds": 10,
        "patterns": [
            {"variable_key": "temperature", "pattern": "sine",
             "config": {"min": 18.0, "max": 28.0, "period_seconds": 300}},
            {"variable_key": "humidity", "pattern": "sine",
             "config": {"min": 40.0, "max": 70.0, "period_seconds": 300, "phase_offset": 3.14159}},
            {"variable_key": "pressure", "pattern": "noise",
             "config": {"center": 1013.0, "amplitude": 5.0}},
        ],
    },
    {
        "name": "[Demo] Weather Station",
        "template": "weather",
        "description": "Auto-created demo simulator — outdoor weather with wind + rain",
        "interval_seconds": 15,
        "patterns": [
            {"variable_key": "temperature", "pattern": "sine",
             "config": {"min": 5.0, "max": 25.0, "period_seconds": 600}},
            {"variable_key": "humidity", "pattern": "sine",
             "config": {"min": 30.0, "max": 90.0, "period_seconds": 600, "phase_offset": 3.14159}},
            {"variable_key": "wind_speed", "pattern": "random_walk",
             "config": {"center": 10.0, "volatility": 2.0, "min_bound": 0.0, "max_bound": 50.0}},
            {"variable_key": "rain_mm", "pattern": "counter",
             "config": {"start": 0.0, "increment": 0.2, "interval_seconds": 300, "reset_at": 50.0}},
        ],
    },
    {
        "name": "[Demo] Motion Sensor",
        "template": "motion",
        "description": "Auto-created demo simulator — PIR motion + ambient light",
        "interval_seconds": 10,
        "patterns": [
            {"variable_key": "motion", "pattern": "step",
             "config": {"values": [False, False, False, True, False, True], "interval_seconds": 30}},
            {"variable_key": "luminance", "pattern": "sine",
             "config": {"min": 0.0, "max": 1000.0, "period_seconds": 300}},
        ],
    },
]


async def seed_simulators(db, *, user: User, org_id: int | None) -> int:
    """Create demo simulators + virtual devices and start them.

    Idempotent: skips simulators whose name already exists for this user.
    Returns the number of newly created simulators.
    """
    created = 0

    for spec in SEED_SIMULATORS:
        # Check if already exists
        res = await db.execute(
            select(SimulatorConfig).where(
                SimulatorConfig.owner_id == user.id,
                SimulatorConfig.name == spec["name"],
            )
        )
        if res.scalar_one_or_none() is not None:
            continue  # already seeded

        # Create virtual device for this simulator
        uid = f"sim-{secrets.token_hex(6)}"
        device = Device(
            device_uid=uid,
            device_type="hardware",
            name=spec["name"].replace("[Demo] ", ""),
            category="hardware",
            owner_user_id=user.id,
            org_id=org_id,
            is_claimed=True,
        )
        db.add(device)
        await db.flush()

        # Create simulator config
        sim = SimulatorConfig(
            org_id=org_id,
            owner_id=user.id,
            device_id=device.id,
            device_uid=device.device_uid,
            name=spec["name"],
            description=spec["description"],
            template=spec["template"],
            variable_patterns=spec["patterns"],
            interval_seconds=spec["interval_seconds"],
            speed_multiplier=1.0,
            is_virtual_device=True,
            is_active=True,
            started_at=datetime.now(timezone.utc),
        )
        db.add(sim)
        await db.flush()

        # Start the simulator worker
        try:
            from app.core import simulator_worker
            simulator_worker.start_simulator(sim.id)
        except Exception as e:
            logger.warning("Could not auto-start simulator %s: %s", sim.id, e)

        created += 1

    await db.commit()
    return created


async def main():
    emails_raw = os.getenv("HUBEX_TEST_EMAILS", DEFAULT_EMAILS)
    password = os.getenv("HUBEX_TEST_PASSWORD", DEFAULT_PASSWORD)
    org_id = int(os.getenv("HUBEX_TEST_ORG_ID", str(DEFAULT_ORG_ID)))
    emails = [e.strip() for e in emails_raw.split(",") if e.strip()]

    print(f"Seeding {len(emails)} test user(s) with role='tester' in org_id={org_id}")
    print(f"Tester caps: {len(ROLE_CAPS['tester'])} capabilities")

    async with AsyncSessionLocal() as db:
        for email in emails:
            status = await seed_test_user(db, email=email, password=password, org_id=org_id)
            print(f"  {email}: {status}")

            # Seed demo simulators for this user
            res = await db.execute(select(User).where(User.email == email))
            user = res.scalar_one()
            sim_count = await seed_simulators(db, user=user, org_id=org_id)
            if sim_count:
                print(f"    + {sim_count} demo simulator(s) created and started")
            else:
                print(f"    (simulators already seeded)")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
