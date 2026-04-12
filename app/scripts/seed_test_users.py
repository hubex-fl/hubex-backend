"""Seed test-user accounts with separate orgs, tester role, and demo simulators.

Each test user gets:
- Their own Organization (isolated devices, variables, dashboards)
- The 'tester' RBAC role (interactive but restricted)
- 3 demo simulators (Temperature, Weather, Motion+GPS) auto-started
- The owner account (account@florianlangen.de) added to their org as 'owner'

Run manually:
    python -m app.scripts.seed_test_users

Idempotent: skips users/orgs/simulators that already exist.
"""

import asyncio
import logging
import re
import secrets

from datetime import datetime, timezone
from sqlalchemy import select

from app.core.capabilities import ROLE_CAPS, resolve_caps_for_role
from app.core.security import hash_password, verify_password
from app.db.models.device import Device
from app.db.models.orgs import Organization, OrganizationUser
from app.db.models.simulator import SimulatorConfig
from app.db.models.user import User
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")


# ── Tester Definitions ─────────────────────────────────────────────────────────

OWNER_EMAIL = "account@florianlangen.de"

TESTERS = [
    {
        "email": "tobiaslangen69@gmail.com",
        "password": "Kx8#mVpL2$nRqT",
        "display_name": "Toby",
        "org_name": "Community Systems",
        "org_slug": "community-systems",
    },
    {
        "email": "mmund@smail.uni-koeln.de",
        "password": "Wf3@jNhD9&bYsG",
        "display_name": "Martin",
        "org_name": "ChaosUhren24.de",
        "org_slug": "chaosuhren24",
    },
    {
        "email": "info@dema-abrechnungsservice.de",
        "password": "Qz7!cXrE4*uPaM",
        "display_name": "Leo",
        "org_name": "DeMa Abrechnungsservice",
        "org_slug": "dema-abrechnungsservice",
    },
    {
        "email": "praegustator@hubextest.tech",
        "password": "Jt5%gBwK6^dFvH",
        "display_name": "praegustator",
        "org_name": "QA Internal",
        "org_slug": "qa-internal",
    },
]

# Also keep the legacy test user (for backward compat)
LEGACY_TEST_EMAIL = "test@hubextest.tech"
LEGACY_TEST_PASSWORD = "HubExDemo2025!"


# ── Simulator Templates ─────────────────────────────────────────────────────────

SEED_SIMULATORS = [
    {
        "name": "[Demo] Temperature Sensor",
        "template": "temperature",
        "description": "Demo simulator — temperature, humidity, pressure",
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
        "description": "Demo simulator — outdoor weather with wind + rain",
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
        "description": "Demo simulator — PIR motion + ambient light + GPS tracking",
        "interval_seconds": 10,
        "patterns": [
            {"variable_key": "motion", "pattern": "step",
             "config": {"values": [False, False, False, True, False, True], "interval_seconds": 30}},
            {"variable_key": "luminance", "pattern": "sine",
             "config": {"min": 0.0, "max": 1000.0, "period_seconds": 300}},
            {"variable_key": "demo.gps", "pattern": "gps_track",
             "config": {
                 "speed_kmh": 15,
                 "waypoints": [
                     {"lat": 50.1109, "lng": 8.6821},
                     {"lat": 50.1133, "lng": 8.6785},
                     {"lat": 50.1155, "lng": 8.6730},
                     {"lat": 50.1180, "lng": 8.6700},
                     {"lat": 50.1155, "lng": 8.6650},
                     {"lat": 50.1120, "lng": 8.6690},
                     {"lat": 50.1109, "lng": 8.6821},
                 ],
             }},
        ],
    },
]


# ── Core Functions ──────────────────────────────────────────────────────────────

async def ensure_org(db, *, name: str, slug: str) -> Organization:
    """Get or create an organization by slug."""
    res = await db.execute(select(Organization).where(Organization.slug == slug))
    org = res.scalar_one_or_none()
    if org:
        return org
    org = Organization(name=name, slug=slug, plan="free", max_devices=50, max_users=10)
    db.add(org)
    await db.flush()
    print(f"  Created org: {name} (id={org.id})")
    return org


async def ensure_user(db, *, email: str, password: str, display_name: str | None = None) -> tuple[User, str]:
    """Get or create a user. Returns (user, status)."""
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()

    tester_caps = resolve_caps_for_role("tester")

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            caps=tester_caps,
            display_name=display_name,
        )
        db.add(user)
        await db.flush()
        return user, "created"
    else:
        if not verify_password(password, user.password_hash):
            user.password_hash = hash_password(password)
        user.caps = tester_caps
        if display_name and not user.display_name:
            user.display_name = display_name
        return user, "updated"


async def ensure_membership(db, *, user_id: int, org_id: int, role: str) -> str:
    """Ensure user is member of org with given role."""
    res = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == user_id,
        )
    )
    ou = res.scalar_one_or_none()
    if ou is None:
        ou = OrganizationUser(org_id=org_id, user_id=user_id, role=role)
        db.add(ou)
        return f"joined ({role})"
    elif ou.role != role:
        ou.role = role
        return f"role→{role}"
    return "ok"


async def seed_simulators_for_org(db, *, user: User, org_id: int) -> int:
    """Create demo simulators + virtual devices for an org. Idempotent."""
    created = 0

    for spec in SEED_SIMULATORS:
        # Check if already exists for this user
        res = await db.execute(
            select(SimulatorConfig).where(
                SimulatorConfig.owner_id == user.id,
                SimulatorConfig.name == spec["name"],
            )
        )
        if res.scalar_one_or_none() is not None:
            continue

        # Create virtual device
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

    return created


async def main():
    print("=" * 60)
    print("HUBEX Test User Seeding — Separate Orgs")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # ── Find the owner account ──────────────────────────────────
        res = await db.execute(select(User).where(User.email == OWNER_EMAIL))
        owner = res.scalar_one_or_none()
        if not owner:
            print(f"WARNING: Owner account {OWNER_EMAIL} not found!")
            print("  Owner will not be added to tester orgs.")
        else:
            print(f"Owner: {OWNER_EMAIL} (id={owner.id})")

        # ── Process each tester ─────────────────────────────────────
        for spec in TESTERS:
            print(f"\n--- {spec['display_name']} ({spec['email']}) ---")

            # 1. Create org
            org = await ensure_org(db, name=spec["org_name"], slug=spec["org_slug"])
            print(f"  Org: {org.name} (id={org.id})")

            # 2. Create user
            user, status = await ensure_user(
                db,
                email=spec["email"],
                password=spec["password"],
                display_name=spec["display_name"],
            )
            print(f"  User: {status} (id={user.id})")

            # 3. Add user to their org as tester
            mem_status = await ensure_membership(db, user_id=user.id, org_id=org.id, role="tester")
            print(f"  Membership: {mem_status}")

            # 4. Set user's default org
            if hasattr(user, "default_org_id"):
                user.default_org_id = org.id

            # 5. Add owner to this org
            if owner:
                owner_status = await ensure_membership(db, user_id=owner.id, org_id=org.id, role="owner")
                print(f"  Owner membership: {owner_status}")

            await db.commit()

            # 6. Seed simulators
            sim_count = await seed_simulators_for_org(db, user=user, org_id=org.id)
            if sim_count:
                print(f"  + {sim_count} simulator(s) created and started")
            else:
                print(f"  (simulators already seeded)")
            await db.commit()

        # ── Legacy test user (keep for backward compat) ─────────────
        print(f"\n--- Legacy: {LEGACY_TEST_EMAIL} ---")
        res = await db.execute(select(User).where(User.email == LEGACY_TEST_EMAIL))
        legacy = res.scalar_one_or_none()
        if legacy:
            legacy.caps = resolve_caps_for_role("tester")
            if not verify_password(LEGACY_TEST_PASSWORD, legacy.password_hash):
                legacy.password_hash = hash_password(LEGACY_TEST_PASSWORD)
            print(f"  Updated (id={legacy.id})")
            await db.commit()
        else:
            print("  Not found, skipping.")

    print("\n" + "=" * 60)
    print("Done! Tester accounts ready.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
