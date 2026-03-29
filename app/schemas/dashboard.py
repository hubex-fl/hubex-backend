from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DashboardWidgetCreate(BaseModel):
    widget_type: str
    variable_key: str
    device_uid: Optional[str] = None
    label: Optional[str] = None
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    display_config: Optional[dict] = None
    grid_col: int = 0
    grid_row: int = 0
    grid_span_w: int = 4
    grid_span_h: int = 1
    sort_order: int = 0


class DashboardWidgetUpdate(BaseModel):
    widget_type: Optional[str] = None
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
    variable_key: str
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
    created_at: datetime
    updated_at: datetime
    widgets: list[DashboardWidgetOut] = []

    model_config = {"from_attributes": True}


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
