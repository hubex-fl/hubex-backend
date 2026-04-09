from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator


class DashboardWidgetCreate(BaseModel):
    widget_type: str
    variable_key: Optional[str] = None
    device_uid: Optional[str] = None
    label: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    display_config: Optional[dict] = None
    grid_col: int = 0
    grid_row: int = 0
    grid_span_w: int = 4
    grid_span_h: int = 3
    sort_order: int = 0


class DashboardWidgetUpdate(BaseModel):
    widget_type: Optional[str] = None
    variable_key: Optional[str] = None
    device_uid: Optional[str] = None
    label: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    display_config: Optional[dict] = None
    grid_col: Optional[int] = None
    grid_row: Optional[int] = None
    grid_span_w: Optional[int] = None
    grid_span_h: Optional[int] = None
    sort_order: Optional[int] = None


class DashboardWidgetOut(BaseModel):
    id: int
    dashboard_id: int
    widget_type: str
    variable_key: Optional[str]
    device_uid: Optional[str]
    label: Optional[str]
    unit: Optional[str]
    min_value: Optional[float]
    max_value: Optional[float]
    display_config: Optional[dict]
    grid_col: int
    grid_row: int
    grid_span_w: int
    grid_span_h: int
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sharing_mode: str = "private"
    is_default: bool = False


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sharing_mode: Optional[str] = None
    is_default: Optional[bool] = None


class DashboardOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    owner_id: int
    sharing_mode: str
    public_token: Optional[str] = None
    has_pin: bool = False
    embed_config: Optional[dict] = None
    kiosk_config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    widgets: list[DashboardWidgetOut] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="wrap")
    @classmethod
    def _compute_has_pin(cls, data, handler):
        # When created from ORM object (from_attributes), read public_pin directly
        if hasattr(data, "public_pin"):
            instance = handler(data)
            instance.has_pin = bool(data.public_pin)
            return instance
        # When created from dict
        if isinstance(data, dict) and "public_pin" in data:
            data = dict(data)
            data["has_pin"] = bool(data.pop("public_pin"))
        return handler(data)


class DashboardSummaryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_default: bool
    sharing_mode: str
    widget_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LayoutUpdate(BaseModel):
    """Bulk update widget positions."""
    widgets: list[dict]  # [{id, grid_col, grid_row, grid_span_w, grid_span_h, sort_order}]


class DashboardCloneRequest(BaseModel):
    """Clone a dashboard with optional new name and entity scope."""
    name: Optional[str] = None
    entity_id: Optional[str] = None  # scope all widgets to devices of this entity


class DashboardEmbedConfig(BaseModel):
    allowed_referers: list[str] = []
    expires_at: Optional[datetime] = None
    max_views: Optional[int] = None


class DashboardKioskConfig(BaseModel):
    auto_slide: bool = False
    slide_interval: int = 30
    slide_dashboards: list[int] = []
    show_header: bool = True
    show_clock: bool = True


class DashboardGenerateSetRequest(BaseModel):
    """Generate a set of dashboards from a template."""
    entity_id: str
    scope_by: str = "devices"  # "devices" or "children"
