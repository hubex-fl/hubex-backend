"""CMS Page schemas."""
from datetime import datetime
from typing import Optional

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
    created_at: datetime
    updated_at: datetime

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
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
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
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


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
