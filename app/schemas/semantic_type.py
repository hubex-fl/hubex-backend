"""Pydantic schemas for the semantic type system."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Optional
import datetime


# --- SemanticType ---

class SemanticTypeBase(BaseModel):
    name: str = Field(..., max_length=64, min_length=1)
    display_name: str = Field(..., max_length=128, min_length=1)
    base_type: str = Field(..., pattern=r"^(bool|int|float|string|json)$")
    unit: Optional[str] = Field(default=None, max_length=32)
    unit_symbol: Optional[str] = Field(default=None, max_length=8)
    value_schema: Optional[dict[str, Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_viz_type: Optional[str] = Field(default=None, max_length=32)
    icon: Optional[str] = Field(default=None, max_length=32)
    color: Optional[str] = Field(default=None, max_length=16)


class SemanticTypeCreate(SemanticTypeBase):
    model_config = ConfigDict(extra="ignore")


class SemanticTypePatch(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=128)
    unit: Optional[str] = Field(default=None, max_length=32)
    unit_symbol: Optional[str] = Field(default=None, max_length=8)
    value_schema: Optional[dict[str, Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_viz_type: Optional[str] = Field(default=None, max_length=32)
    icon: Optional[str] = Field(default=None, max_length=32)
    color: Optional[str] = Field(default=None, max_length=16)
    model_config = ConfigDict(extra="ignore")


class SemanticTypeOut(SemanticTypeBase):
    id: int
    is_builtin: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)


# --- TriggerTemplate ---

class TriggerTemplateOut(BaseModel):
    id: int
    semantic_type_id: int
    trigger_name: str
    display_name: str
    description: Optional[str] = None
    config_schema: Optional[dict[str, Any]] = None
    icon: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- UnitConversion ---

class UnitConversionOut(BaseModel):
    id: int
    semantic_type_id: int
    from_unit: str
    to_unit: str
    formula: str
    is_default: bool
    model_config = ConfigDict(from_attributes=True)


# --- Detail (includes nested) ---

class SemanticTypeDetailOut(SemanticTypeOut):
    triggers: list[TriggerTemplateOut] = []
    conversions: list[UnitConversionOut] = []
