from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, AliasChoices

Scope = Literal["device", "global", "user"]
ValueType = Literal["string", "int", "float", "bool", "json"]


class VariableDefinitionIn(BaseModel):
    key: str = Field(min_length=3, max_length=128)
    scope: Scope
    value_type: ValueType = Field(validation_alias=AliasChoices("value_type", "valueType"))
    default_value: Any | None = Field(
        default=None, validation_alias=AliasChoices("default_value", "defaultValue")
    )
    description: str | None = None
    unit: str | None = None
    min_value: float | None = Field(default=None, validation_alias=AliasChoices("min_value", "minValue"))
    max_value: float | None = Field(default=None, validation_alias=AliasChoices("max_value", "maxValue"))
    enum_values: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("enum_values", "enumValues")
    )
    regex: str | None = None
    is_secret: bool = Field(default=False, validation_alias=AliasChoices("is_secret", "isSecret"))
    is_readonly: bool = Field(default=False, validation_alias=AliasChoices("is_readonly", "isReadonly", "read_only", "readOnly"))
    user_writable: bool = Field(default=True, validation_alias=AliasChoices("user_writable", "userWritable"))
    device_writable: bool = Field(default=False, validation_alias=AliasChoices("device_writable", "deviceWritable"))
    allow_device_override: bool = Field(
        default=True, validation_alias=AliasChoices("allow_device_override", "allowDeviceOverride")
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class VariableDefinitionOut(BaseModel):
    key: str
    scope: Scope
    value_type: ValueType
    default_value: Any | None
    description: str | None
    unit: str | None
    min_value: float | None
    max_value: float | None
    enum_values: list[str] | None
    regex: str | None
    is_secret: bool
    is_readonly: bool
    user_writable: bool
    device_writable: bool
    allow_device_override: bool
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


class VariableSetIn(BaseModel):
    key: str
    scope: Scope
    device_uid: str | None = Field(default=None, validation_alias=AliasChoices("device_uid", "deviceUid"))
    value: Any
    expected_version: int | None = Field(
        default=None, validation_alias=AliasChoices("expected_version", "expectedVersion")
    )
    force: bool = Field(default=False)

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


class EffectiveVariableOut(BaseModel):
    key: str
    value: Any | None
    scope: Scope
    device_uid: str | None
    version: int | None
    updated_at: datetime | None
    is_secret: bool
    source: Literal["default", "global", "device_override"]
    precedence: int
    resolved_type: ValueType | None = None
    constraints: dict[str, Any] | None = None


class EffectiveVariablesOut(BaseModel):
    device_uid: str
    computed_at: datetime
    effective_version: str
    items: list[EffectiveVariableOut]


class VariableAppliedItemIn(BaseModel):
    key: str
    version: int | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class VariableAppliedIn(BaseModel):
    device_uid: str = Field(validation_alias=AliasChoices("device_uid", "deviceUid"))
    applied: list[VariableAppliedItemIn]

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


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
