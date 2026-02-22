import argparse
import asyncio
import os
from typing import Iterable

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.db.models.user import User
from app.db.session import AsyncSessionLocal

DEFAULT_EMAIL = "codex+20251219002029@example.com"
DEFAULT_PASSWORD = "Test1234!"
DEFAULT_CAPS = [
    "devices.read",
    "events.read",
    "effects.read",
    "vars.read",
    "devices.token.reissue",
]


def _merge_caps(*groups: Iterable[str] | None) -> list[str]:
    merged: set[str] = set()
    for group in groups:
        if not group:
            continue
        merged.update([cap for cap in group if cap])
    return sorted(merged)


async def ensure_dev_user_caps_db(
    db,
    *,
    email: str,
    password: str,
    caps: list[str],
    force_password: bool,
) -> User:
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user is None:
        user = User(email=email, password_hash=hash_password(password), caps=_merge_caps([], caps))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    if force_password or not verify_password(password, user.password_hash):
        user.password_hash = hash_password(password)
    user.caps = _merge_caps(user.caps, caps)
    await db.commit()
    await db.refresh(user)
    return user


async def ensure_dev_user_caps(
    email: str,
    password: str,
    caps: list[str],
    *,
    force_password: bool,
) -> User:
    async with AsyncSessionLocal() as db:
        return await ensure_dev_user_caps_db(
            db,
            email=email,
            password=password,
            caps=caps,
            force_password=force_password,
        )


async def _run(args: argparse.Namespace) -> int:
    email = args.email or os.getenv("HUBEX_DEV_EMAIL", DEFAULT_EMAIL)
    password = args.password or os.getenv("HUBEX_DEV_PASSWORD", DEFAULT_PASSWORD)
    caps = args.caps or os.getenv("HUBEX_DEV_CAPS", "")
    force_password = args.force_password or os.getenv("HUBEX_DEV_FORCE_PASSWORD", "1") == "1"

    override_list = [c.strip() for c in str(caps).split(",") if c.strip()] if caps else []
    cap_list = _merge_caps(DEFAULT_CAPS, override_list)
    user = await ensure_dev_user_caps(
        email=email,
        password=password,
        caps=cap_list,
        force_password=force_password,
    )
    print(f"OK: dev user caps ensured: email={user.email} caps={user.caps}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure dev/test user caps in DB (dev only).")
    parser.add_argument("--email", help="Dev user email", default=None)
    parser.add_argument("--password", help="Dev user password", default=None)
    parser.add_argument("--caps", help="Comma-separated caps list", default=None)
    parser.add_argument("--force-password", action="store_true", help="Always reset password hash")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
