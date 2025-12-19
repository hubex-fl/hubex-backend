from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import os

from app.db.models.device import Device


class DeviceState(str, Enum):
    seen = "seen"
    paired = "paired"
    claimed = "claimed"
    active = "active"


ACTIVE_WINDOW_SECONDS = int(os.getenv("DEVICE_ACTIVE_WINDOW_SECONDS", "300"))


def derive_device_states(
    device: Device,
    *,
    pairing_active: bool = False,
    now: datetime | None = None,
) -> set[DeviceState]:
    states: set[DeviceState] = set()
    if device is None:
        return states

    last_seen_at = device.last_seen_at
    if last_seen_at is not None:
        states.add(DeviceState.seen)
        if ACTIVE_WINDOW_SECONDS > 0:
            delta = (now or datetime.now(timezone.utc)) - last_seen_at
            if delta.total_seconds() <= ACTIVE_WINDOW_SECONDS:
                states.add(DeviceState.active)

    if pairing_active:
        states.add(DeviceState.paired)
    if device.owner_user_id is not None:
        states.add(DeviceState.claimed)
    return states
