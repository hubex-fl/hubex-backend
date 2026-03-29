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


# ── Automation Steps (M19: Ketten & Sequenzen) ────────────────────────────────

class AutomationStepCreate(BaseModel):
    step_order: int = Field(default=0, ge=0)
    action_type: str
    action_config: dict[str, Any] = Field(default_factory=dict)
    delay_seconds: int = Field(default=0, ge=0)
    condition_type: Optional[str] = None  # "branch" or None
    condition_config: Optional[dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")


class AutomationStepUpdate(BaseModel):
    step_order: Optional[int] = Field(default=None, ge=0)
    action_type: Optional[str] = None
    action_config: Optional[dict[str, Any]] = None
    delay_seconds: Optional[int] = Field(default=None, ge=0)
    condition_type: Optional[str] = None
    condition_config: Optional[dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")


class AutomationStepOut(BaseModel):
    id: int
    rule_id: int
    step_order: int
    action_type: str
    action_config: dict[str, Any]
    delay_seconds: int
    condition_type: Optional[str] = None
    condition_config: Optional[dict[str, Any]] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ── Trigger Templates (M19: Typsystem-Integration) ────────────────────────────

class TriggerTemplateOut(BaseModel):
    id: int
    trigger_name: str
    display_name: str
    description: Optional[str] = None
    config_schema: Optional[dict[str, Any]] = None
    semantic_type_name: Optional[str] = None
    icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Automation Templates (M19: Built-in Quick-start) ──────────────────────────

class AutomationTemplate(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    trigger_type: str
    trigger_config: dict[str, Any]
    action_type: str
    action_config: dict[str, Any]
    cooldown_seconds: int = 300


AUTOMATION_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "threshold_alert",
        "name": "Threshold Alert",
        "description": "Alert when a variable exceeds a value",
        "icon": "chart-bar",
        "trigger_type": "variable_threshold",
        "trigger_config": {"variable_key": "", "operator": "gt", "value": 0},
        "action_type": "create_alert_event",
        "action_config": {"severity": "warning", "message": "Threshold exceeded"},
        "cooldown_seconds": 300,
    },
    {
        "id": "device_offline_alert",
        "name": "Device Offline Alert",
        "description": "Alert when any device goes offline",
        "icon": "wifi-off",
        "trigger_type": "device_offline",
        "trigger_config": {},
        "action_type": "create_alert_event",
        "action_config": {"severity": "critical", "message": "Device went offline"},
        "cooldown_seconds": 600,
    },
    {
        "id": "variable_forward",
        "name": "Variable Forwarding",
        "description": "Copy a variable value to another variable",
        "icon": "arrow-right",
        "trigger_type": "variable_threshold",
        "trigger_config": {"variable_key": "", "operator": "gt", "value": 0},
        "action_type": "set_variable",
        "action_config": {"variable_key": "", "value": "", "scope": "global"},
        "cooldown_seconds": 60,
    },
    {
        "id": "webhook_on_telemetry",
        "name": "Webhook on Telemetry",
        "description": "Send a webhook when telemetry arrives",
        "icon": "globe",
        "trigger_type": "telemetry_received",
        "trigger_config": {},
        "action_type": "call_webhook",
        "action_config": {"url": "", "method": "POST"},
        "cooldown_seconds": 60,
    },
    {
        "id": "geofence_alert",
        "name": "Geofence Alert",
        "description": "Alert when device leaves a zone",
        "icon": "map-pin",
        "trigger_type": "variable_geofence",
        "trigger_config": {
            "variable_key": "",
            "geofence_type": "circle",
            "exit_or_enter": "exit",
            "center": {"lat": 0, "lng": 0},
            "radius_m": 500,
        },
        "action_type": "create_alert_event",
        "action_config": {"severity": "warning", "message": "Device left geofence"},
        "cooldown_seconds": 300,
    },
]
