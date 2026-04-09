"""Pydantic schemas for Custom API Builder endpoints."""

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator

# Regex: only letters, digits, hyphens, underscores, slashes, dots
_PATH_CHARS_RE = re.compile(r"^[a-zA-Z0-9\-_/\.]+$")


class SourceConfigBase(BaseModel):
    """Source configuration for an endpoint — defines what data to query or write."""

    type: Literal[
        "variables", "devices", "entities", "alerts", "events",
        "status_snapshot", "set_variable",
    ]
    # Read filters
    variable_keys: list[str] | None = None
    device_uids: list[str] | None = None
    entity_ids: list[int] | None = None
    # Aggregation
    aggregation: Literal["avg", "min", "max", "sum"] | None = None
    time_range: Literal["1h", "24h", "7d", "30d"] | None = None
    group_by: Literal["hour", "day", "month"] | None = None
    # Response format
    format: Literal["json", "csv"] = "json"
    # Write configuration (for set_variable)
    allowed_variable_keys: list[str] | None = None
    device_uid: str | None = None


class EndpointCreate(BaseModel):
    """Create a new custom API endpoint."""

    name: str = Field(..., min_length=1, max_length=100)
    path: str = Field(..., min_length=1, max_length=200)
    method: Literal["GET", "POST"] = "GET"
    description: str | None = None
    source_config: SourceConfigBase
    auth_type: Literal["api_key", "bearer", "none"] = "api_key"
    rate_limit: int = Field(default=100, ge=1, le=10000)
    write_enabled: bool = False

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("path must be at least 2 characters (e.g. /x)")
        if len(v) > 200:
            raise ValueError("path must not exceed 200 characters")
        if not v.startswith("/"):
            raise ValueError("path must start with /")
        if v.endswith("/") and len(v) > 1:
            raise ValueError("path must not end with a trailing slash")
        if "//" in v:
            raise ValueError("path must not contain double slashes (//)")
        if ".." in v:
            raise ValueError("path must not contain path traversal (..)")
        # Only allow safe characters (letters, digits, hyphens, underscores, slashes, dots)
        path_body = v[1:]  # strip leading /
        if path_body and not _PATH_CHARS_RE.match(path_body):
            raise ValueError(
                "path may only contain letters, numbers, hyphens, underscores, slashes, and dots"
            )
        return v

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, v: str) -> str:
        return v.upper()


class EndpointUpdate(BaseModel):
    """Update an existing custom API endpoint."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    source_config: SourceConfigBase | None = None
    auth_type: Literal["api_key", "bearer", "none"] | None = None
    rate_limit: int | None = Field(default=None, ge=1, le=10000)
    write_enabled: bool | None = None
    enabled: bool | None = None


class EndpointOut(BaseModel):
    """Custom API endpoint response."""

    id: int
    name: str
    path: str
    method: str
    description: str | None
    source_config: dict
    auth_type: str
    api_key: str | None
    rate_limit: int
    write_enabled: bool
    enabled: bool
    request_count: int
    last_called_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    # Computed URL hint for the consumer
    call_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EndpointSummaryOut(BaseModel):
    """Lightweight endpoint summary for list views."""

    id: int
    name: str
    path: str
    method: str
    enabled: bool
    auth_type: str
    request_count: int
    last_called_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EndpointTrafficOut(BaseModel):
    """Traffic statistics for a custom endpoint."""

    id: int
    name: str
    path: str
    request_count: int
    last_called_at: datetime | None
    rate_limit: int

    model_config = ConfigDict(from_attributes=True)


class RegenerateKeyOut(BaseModel):
    """Response after regenerating an API key."""

    api_key: str


class PreviewOut(BaseModel):
    """Preview what a custom endpoint would return."""

    endpoint_id: int
    path: str
    method: str
    source_config: dict
    sample_data: Any


class SetVariablePayload(BaseModel):
    """Payload for POST endpoints that set variables."""

    variable_key: str
    value: Any
    device_uid: str | None = None
