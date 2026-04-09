from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TourStepSchema(BaseModel):
    """A single step in a guided tour."""
    id: str
    page: Optional[str] = None
    target: Optional[str] = None
    action: str = "spotlight"
    title: str
    text: str
    position: str = "bottom"
    delay: Optional[int] = None
    duration: Optional[int] = None


class TourCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    steps: list[TourStepSchema] = []
    is_public: bool = False
    category: str = "custom"


class TourUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    steps: Optional[list[TourStepSchema]] = None
    is_public: Optional[bool] = None
    category: Optional[str] = None


class TourOut(BaseModel):
    id: int
    org_id: Optional[int]
    owner_id: int
    name: str
    description: Optional[str]
    steps: list[TourStepSchema]
    is_public: bool
    public_token: Optional[str] = None
    category: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TourSummaryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    step_count: int
    is_public: bool
    category: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
