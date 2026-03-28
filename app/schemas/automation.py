"""Pydantic schemas for AutomationRule and AutomationFireLog."""
from __future__ import annotations

from typing import Any, Optional
import datetime

from pydantic import BaseModel, ConfigDict, Field

VALID_TRIGGER_TYPES = {
    "variable_threshold",
    "variable_geofence",
    "device_offline",
    "telemetry_received",
}

VALID_ACTION_TYPES = {
    "set_variable",
    "call_webhook",
    "create_alert_event",
    "emit_system_event",
}


class AutomationRuleBase(BaseModel):
    name: str = Field(..., max_length=120, min_length=1)
    description: Optional[str] = None
    enabled: bool = True
    trigger_type: str
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    action_type: str
    action_config: dict[str, Any] = Field(default_factory=dict)
    cooldown_seconds: int = Field(default=300, ge=0)


class AutomationRuleCreate(AutomationRuleBase):
    model_config = ConfigDict(extra="ignore")


class AutomationRulePatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120, min_length=1)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    action_type: Optional[str] = None
    action_config: Optional[dict[str, Any]] = None
    cooldown_seconds: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(extra="ignore")


class AutomationRuleOut(AutomationRuleBase):
    id: int
    org_id: Optional[int] = None
    fire_count: int
    last_fired_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationFireLogOut(BaseModel):
    id: int
    rule_id: int
    fired_at: datetime.datetime
    success: bool
    error_message: Optional[str] = None
    context_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
