"""Site Settings schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class SiteSettingsBase(BaseModel):
    site_title: Optional[str] = None
    site_tagline: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    bg_color: Optional[str] = None
    text_color: Optional[str] = None

    default_meta_title: Optional[str] = None
    default_meta_description: Optional[str] = None
    default_og_image: Optional[str] = None
    twitter_handle: Optional[str] = None

    google_analytics_id: Optional[str] = None
    plausible_domain: Optional[str] = None

    footer_text: Optional[str] = None
    footer_links: Optional[list[dict[str, Any]]] = None

    custom_css: Optional[str] = None
    custom_head_html: Optional[str] = None
    custom_footer_html: Optional[str] = None


class SiteSettingsUpdate(SiteSettingsBase):
    pass


class SiteSettingsOut(BaseModel):
    id: int
    org_id: Optional[int]
    site_title: str
    site_tagline: Optional[str]
    logo_url: Optional[str]
    favicon_url: Optional[str]
    primary_color: str
    accent_color: str
    bg_color: str
    text_color: str

    default_meta_title: Optional[str]
    default_meta_description: Optional[str]
    default_og_image: Optional[str]
    twitter_handle: Optional[str]

    google_analytics_id: Optional[str]
    plausible_domain: Optional[str]

    footer_text: Optional[str]
    footer_links: Optional[list[dict[str, Any]]]

    custom_css: Optional[str]
    custom_head_html: Optional[str]
    custom_footer_html: Optional[str]

    updated_at: datetime

    model_config = {"from_attributes": True}


class SiteSettingsPublicOut(BaseModel):
    """Safe subset for public consumption (no analytics IDs)."""
    site_title: str
    site_tagline: Optional[str]
    logo_url: Optional[str]
    favicon_url: Optional[str]
    primary_color: str
    accent_color: str
    bg_color: str
    text_color: str
    default_meta_title: Optional[str]
    default_meta_description: Optional[str]
    default_og_image: Optional[str]
    twitter_handle: Optional[str]
    footer_text: Optional[str]
    footer_links: Optional[list[dict[str, Any]]]
    custom_css: Optional[str]
    custom_head_html: Optional[str]
    custom_footer_html: Optional[str]
    google_analytics_id: Optional[str]
    plausible_domain: Optional[str]
