"""Media Asset schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MediaAssetOut(BaseModel):
    id: int
    filename: str
    public_url: str
    mime_type: str
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    thumbnail_url: Optional[str] = None
    kind: str = "other"  # images|videos|audio|documents|archives|other
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaAssetUpdate(BaseModel):
    alt_text: Optional[str] = None
    filename: Optional[str] = None


class MediaAssetListOut(BaseModel):
    items: list[MediaAssetOut]
    total: int
    page: int
    page_size: int
