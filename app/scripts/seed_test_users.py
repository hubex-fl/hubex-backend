"""Sprint 9 — Seed test-user accounts with the 'tester' role.

Creates (or updates) test accounts on the hubextest.tech demo instance.
Each test user gets the 'tester' RBAC role which gives them interactive
access to devices, variables, dashboards, automations, and simulators
but NOT to config, org admin, CMS publish, webhooks, OTA, or API keys.

Run manually:
    python -m app.scripts.seed_test_users

Or add to the daily-reset cron on the VPS so test users survive resets.

Environment variables (all optional):
    HUBEX_TEST_EMAILS   — comma-separated emails (default: test@hubextest.tech)
    HUBEX_TEST_PASSWORD — shared password (default: HubExDemo2025!)
    HUBEX_TEST_ORG_ID   — org to assign tester role in (default: 1)
"""

import asyncio
import os

from sqlalchemy import select

from app.core.capabilities import ROLE_CAPS, resolve_caps_for_role
from app.core.security import hash_password, verify_password
from app.db.models.orgs import OrganizationUser
from app.db.models.user import User
from app.db.session import AsyncSessionLocal


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

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
