from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field


class DeviceListItem(BaseModel):
    id: int
    device_uid: str
    device_type: Optional[str] = "unknown"
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
    # M15 identity fields
    name: Optional[str] = None
    category: str = "hardware"
    icon: Optional[str] = None


class DeviceDetailItem(BaseModel):
    id: int
    device_uid: str
    device_type: Optional[str] = "unknown"
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
    # M15 identity fields
    category: str = "hardware"
    icon: Optional[str] = None
    location_name: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    auto_discovery: bool = True


class DevicePatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    category: Optional[str] = Field(default=None, pattern=r"^(hardware|service|bridge|agent)$")
    icon: Optional[str] = Field(default=None, max_length=32)
    device_type: Optional[str] = Field(default=None, max_length=32)
    location_name: Optional[str] = Field(default=None, max_length=256)
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    auto_discovery: Optional[bool] = None
