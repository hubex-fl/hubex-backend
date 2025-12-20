from datetime import datetime
from typing import Iterable, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.device import Device
from app.db.models.pairing import PairingSession
from app.db.models.tasks import Task


async def fetch_pairing_active_uids(
    db: AsyncSession, device_uids: Iterable[str], now: datetime
) -> set[str]:
    uids = list(device_uids)
    if not uids:
        return set()
    res = await db.execute(
        select(PairingSession.device_uid).where(
            PairingSession.device_uid.in_(uids),
            PairingSession.is_used.is_(False),
            PairingSession.expires_at > now,
        )
    )
    return {row[0] for row in res.all()}


async def fetch_busy_device_ids(
    db: AsyncSession, device_ids: Iterable[int], now: datetime
) -> set[int]:
    ids = list(device_ids)
    if not ids:
        return set()
    res = await db.execute(
        select(Task.client_id).where(
            Task.client_id.in_(ids),
            Task.lease_expires_at.is_not(None),
            Task.lease_expires_at > now,
            Task.lease_token.is_not(None),
            Task.status == "in_flight",
        )
    )
    return {row[0] for row in res.all()}


def derive_state(
    device: Device, pairing_active: bool, busy: bool
) -> Tuple[str, bool]:
    claimed = device.owner_user_id is not None or device.is_claimed
    if device.last_seen_at is None:
        return "unprovisioned", claimed
    if busy:
        return "busy", claimed
    if claimed:
        return "claimed", claimed
    if pairing_active:
        return "pairing_active", claimed
    return "provisioned_unclaimed", claimed

