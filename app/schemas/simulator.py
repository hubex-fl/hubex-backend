from datetime import datetime
from typing import Optional, Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pattern types
# ---------------------------------------------------------------------------

PatternType = Literal[
    "sine",
    "random_walk",
    "step",
    "ramp",
    "counter",
    "gps_track",
    "noise",
    "formula",
    "csv_replay",
    "manual",
]


class VariablePattern(BaseModel):
    variable_key: str = Field(..., min_length=1, max_length=128)
    pattern: PatternType
    config: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------

class SimulatorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    template: Optional[str] = None
    variable_patterns: list[VariablePattern] = Field(default_factory=list)
    interval_seconds: int = Field(default=15, ge=1, le=86400)
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=1000.0)
    is_virtual_device: bool = True
    # If attaching to an existing device instead of creating virtual:
    device_uid: Optional[str] = None


class SimulatorUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    variable_patterns: Optional[list[VariablePattern]] = None
    interval_seconds: Optional[int] = Field(default=None, ge=1, le=86400)
    speed_multiplier: Optional[float] = Field(default=None, ge=0.1, le=1000.0)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class SimulatorOut(BaseModel):
    id: int
    org_id: Optional[int] = None
    owner_id: int
    device_id: Optional[int] = None
    device_uid: Optional[str] = None
    name: str
    description: Optional[str] = None
    template: Optional[str] = None
    variable_patterns: list[VariablePattern] = []
    interval_seconds: int = 15
    speed_multiplier: float = 1.0
    is_active: bool = False
    is_virtual_device: bool = True
    total_points_sent: int = 0
    started_at: Optional[datetime] = None
    last_value_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Quick Pulse (from Device Detail page)
# ---------------------------------------------------------------------------

class SimulatorQuickPulse(BaseModel):
    device_uid: str = Field(..., min_length=1)
    variable_key: str = Field(..., min_length=1)
    value: Any


# ---------------------------------------------------------------------------
# Template listing
# ---------------------------------------------------------------------------

class TemplateInfo(BaseModel):
    key: str
    name: str
    description: str
    variable_patterns: list[VariablePattern]
