"""CMS Page schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CmsPageBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    content_html: str = ""
    content_mode: str = "html"  # "html" | "markdown" | "simple"
    layout: str = "default"  # "default" | "landing" | "minimal" | "fullscreen"
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image: Optional[str] = None
    blocks: Optional[list[dict[str, Any]]] = None
    # Hierarchy
    parent_id: Optional[int] = None
    menu_order: int = 0
    show_in_menu: bool = True


class CmsPageCreate(CmsPageBase):
    visibility: str = "private"
    published: bool = False


class CmsPageUpdate(BaseModel):
    slug: Optional[str] = Field(default=None, max_length=128)
    title: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = None
    content_html: Optional[str] = None
    content_mode: Optional[str] = None
    layout: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image: Optional[str] = None
    visibility: Optional[str] = None
    published: Optional[bool] = None
    embed_allowed_origins: Optional[list[str]] = None
    blocks: Optional[list[dict[str, Any]]] = None
    parent_id: Optional[int] = None
    menu_order: Optional[int] = None
    show_in_menu: Optional[bool] = None


class CmsPageMove(BaseModel):
    parent_id: Optional[int] = None
    menu_order: int = 0


class CmsPageTreeNode(BaseModel):
    id: int
    slug: str
    title: str
    layout: str
    visibility: str
    published: bool
    parent_id: Optional[int] = None
    menu_order: int = 0
    show_in_menu: bool = True
    children: list["CmsPageTreeNode"] = []

    model_config = {"from_attributes": True}


class CmsPageOut(BaseModel):
    id: int
    org_id: Optional[int]
    owner_id: int
    slug: str
    title: str
    description: Optional[str]
    content_html: str
    content_mode: str
    layout: str
    meta_title: Optional[str]
    meta_description: Optional[str]
    og_image: Optional[str]
    visibility: str
    public_token: Optional[str]
    has_pin: bool = False
    embed_allowed_origins: Optional[list] = None
    published: bool
    published_at: Optional[datetime]
    status: str = "draft"
    scheduled_at: Optional[datetime] = None
    view_count: int = 0
    last_viewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    blocks: Optional[list[dict[str, Any]]] = None
    parent_id: Optional[int] = None
    menu_order: int = 0
    show_in_menu: bool = True

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_pin(cls, obj) -> "CmsPageOut":
        data = {
            "id": obj.id,
            "org_id": obj.org_id,
            "owner_id": obj.owner_id,
            "slug": obj.slug,
            "title": obj.title,
            "description": obj.description,
            "content_html": obj.content_html or "",
            "content_mode": obj.content_mode,
            "layout": obj.layout,
            "meta_title": obj.meta_title,
            "meta_description": obj.meta_description,
            "og_image": obj.og_image,
            "visibility": obj.visibility,
            "public_token": obj.public_token,
            "has_pin": bool(obj.public_pin),
            "embed_allowed_origins": obj.embed_allowed_origins,
            "published": obj.published,
            "published_at": obj.published_at,
            "status": getattr(obj, "status", "draft") or "draft",
            "scheduled_at": getattr(obj, "scheduled_at", None),
            "view_count": int(getattr(obj, "view_count", 0) or 0),
            "last_viewed_at": getattr(obj, "last_viewed_at", None),
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "blocks": getattr(obj, "blocks", None),
            "parent_id": getattr(obj, "parent_id", None),
            "menu_order": getattr(obj, "menu_order", 0) or 0,
            "show_in_menu": bool(getattr(obj, "show_in_menu", True)),
        }
        return cls(**data)


class CmsPageSummaryOut(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str]
    layout: str
    visibility: str
    published: bool
    published_at: Optional[datetime]
    status: str = "draft"
    scheduled_at: Optional[datetime] = None
    view_count: int = 0
    last_viewed_at: Optional[datetime] = None
    updated_at: datetime
    created_at: datetime
    parent_id: Optional[int] = None
    menu_order: int = 0
    show_in_menu: bool = True

    model_config = {"from_attributes": True}


class CmsPageScheduleIn(BaseModel):
    published_at: datetime


class CmsPagePublicOut(BaseModel):
    """Safe subset of fields for public viewing."""
    slug: str
    title: str
    description: Optional[str]
    content_html: str  # already with template vars substituted server-side
    content_mode: str
    layout: str
    meta_title: Optional[str]
    meta_description: Optional[str]
    og_image: Optional[str]
    published_at: Optional[datetime]


# ── Version schemas ──────────────────────────────────────────────────────

class CmsPageVersionSummary(BaseModel):
    id: int
    version_num: int
    title: str
    created_by: Optional[int]
    created_at: datetime
    note: Optional[str]

    model_config = {"from_attributes": True}


class CmsPageVersionOut(BaseModel):
    id: int
    page_id: int
    version_num: int
    title: str
    content_html: str
    blocks: Optional[list[dict[str, Any]]] = None
    created_by: Optional[int]
    created_at: datetime
    note: Optional[str]

    model_config = {"from_attributes": True}
