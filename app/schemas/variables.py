from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, AliasChoices

Scope = Literal["device", "global"]
ValueType = Literal["string", "int", "float", "bool", "json"]


class VariableDefinitionIn(BaseModel):
    key: str = Field(min_length=3, max_length=128)
    scope: Scope
    value_type: ValueType = Field(validation_alias=AliasChoices("value_type", "valueType"))
    default_value: Any | None = Field(
        default=None, validation_alias=AliasChoices("default_value", "defaultValue")
    )
    description: str | None = None
    is_secret: bool = Field(default=False, validation_alias=AliasChoices("is_secret", "isSecret"))
    is_readonly: bool = Field(default=False, validation_alias=AliasChoices("is_readonly", "isReadonly"))

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class VariableDefinitionOut(BaseModel):
    key: str
    scope: Scope
    value_type: ValueType
    default_value: Any | None
    description: str | None
    is_secret: bool
    is_readonly: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VariableValueIn(BaseModel):
    key: str
    scope: Scope
    device_uid: str | None = Field(default=None, validation_alias=AliasChoices("device_uid", "deviceUid"))
    value: Any
    expected_version: int | None = Field(
        default=None, validation_alias=AliasChoices("expected_version", "expectedVersion")
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class VariableValueOut(BaseModel):
    key: str
    scope: Scope
    device_uid: str | None
    value: Any
    version: int | None
    updated_at: datetime | None
    is_secret: bool


class DeviceVariablesOut(BaseModel):
    device_uid: str
    globals: list[VariableValueOut]
    device: list[VariableValueOut]


class VariableAuditOut(BaseModel):
    variable_key: str
    scope: Scope
    device_uid: str | None
    old_value: Any | None
    new_value: Any | None
    old_version: int | None
    new_version: int | None
    actor_type: str
    actor_user_id: int | None
    actor_device_id: int | None
    request_id: str | None
    note: str | None
    created_at: datetime
