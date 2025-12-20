from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel


class DeviceListItem(BaseModel):
    id: int
    device_uid: str
    claimed: bool
    last_seen: Optional[datetime]
    online: bool
    health: Literal["ok", "stale", "dead"]
    last_seen_age_seconds: Optional[int]
    state: Literal[
        "unprovisioned",
        "provisioned_unclaimed",
        "pairing_active",
        "claimed",
        "busy",
    ]
    pairing_active: bool
    busy: bool


class DeviceDetailItem(BaseModel):
    id: int
    device_uid: str
    name: Optional[str]
    firmware_version: Optional[str]
    capabilities: Optional[dict]
    last_seen_at: Optional[datetime]
    owner_user_id: Optional[int]
    is_claimed: bool
    created_at: datetime
    health: Literal["ok", "stale", "dead"]
    last_seen_age_seconds: Optional[int]
    state: Literal[
        "unprovisioned",
        "provisioned_unclaimed",
        "pairing_active",
        "claimed",
        "busy",
    ]
    pairing_active: bool
    busy: bool
