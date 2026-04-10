"""CMS Form schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CmsFormBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    slug: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    fields: list[dict[str, Any]] = Field(default_factory=list)
    submit_button_text: str = "Submit"
    success_message: str = "Thank you!"
    action: str = "store"  # "store" | "email" | "webhook" | "both"
    email_to: Optional[str] = None
    webhook_url: Optional[str] = None
    enabled: bool = True


class CmsFormCreate(CmsFormBase):
    pass


class CmsFormUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=256)
    slug: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = None
    fields: Optional[list[dict[str, Any]]] = None
    submit_button_text: Optional[str] = None
    success_message: Optional[str] = None
    action: Optional[str] = None
    email_to: Optional[str] = None
    webhook_url: Optional[str] = None
    enabled: Optional[bool] = None


class CmsFormOut(BaseModel):
    id: int
    org_id: Optional[int]
    owner_id: int
    name: str
    slug: str
    description: Optional[str]
    fields: list[dict[str, Any]]
    submit_button_text: str
    success_message: str
    action: str
    email_to: Optional[str]
    webhook_url: Optional[str]
    enabled: bool
    submission_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CmsFormSummaryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    enabled: bool
    action: str
    submission_count: int = 0
    updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class CmsFormPublicOut(BaseModel):
    """Public-facing form schema (safe subset, returned to unauthenticated clients)."""
    name: str
    slug: str
    description: Optional[str]
    fields: list[dict[str, Any]]
    submit_button_text: str
    success_message: str


class CmsFormSubmissionCreate(BaseModel):
    data: dict[str, Any]


class CmsFormSubmissionOut(BaseModel):
    id: int
    form_id: int
    data: dict[str, Any]
    submitted_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    read: bool

    model_config = {"from_attributes": True}
