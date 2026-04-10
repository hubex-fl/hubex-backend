"""CMS Menu schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CmsMenuBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    location: str = Field(..., min_length=1, max_length=64)
    items: Optional[list[dict[str, Any]]] = None


class CmsMenuCreate(CmsMenuBase):
    pass


class CmsMenuUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    location: Optional[str] = Field(default=None, max_length=64)
    items: Optional[list[dict[str, Any]]] = None


class CmsMenuOut(BaseModel):
    id: int
    org_id: Optional[int]
    owner_id: int
    name: str
    location: str
    items: Optional[list[dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CmsMenuPublicOut(BaseModel):
    """Safe subset of menu fields for public rendering."""
    name: str
    location: str
    items: Optional[list[dict[str, Any]]] = None
