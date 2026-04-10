"""Site Settings API — global branding, SEO, analytics, footer."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.site_settings import SiteSettings
from app.db.models.user import User
from app.schemas.site_settings import (
    SiteSettingsOut,
    SiteSettingsPublicOut,
    SiteSettingsUpdate,
)

router = APIRouter(prefix="/site", tags=["site-settings"])


async def _get_or_create_settings(db: AsyncSession) -> SiteSettings:
    """Return the single SiteSettings row (always id=1). Create with defaults if missing."""
    res = await db.execute(select(SiteSettings).order_by(SiteSettings.id.asc()).limit(1))
    s = res.scalar_one_or_none()
    if s is not None:
        return s
    # Create defaults
    s = SiteSettings(
        site_title="HUBEX",
        primary_color="#F5A623",
        accent_color="#2DD4BF",
        bg_color="#111110",
        text_color="#E5E5E5",
        updated_at=datetime.now(timezone.utc),
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@router.get("/settings", response_model=SiteSettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return current site settings (creates defaults on first access)."""
    s = await _get_or_create_settings(db)
    return SiteSettingsOut.model_validate(s, from_attributes=True)


@router.put("/settings", response_model=SiteSettingsOut)
async def update_settings(
    data: SiteSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = await _get_or_create_settings(db)
    payload = data.model_dump(exclude_none=True)
    for field, value in payload.items():
        setattr(s, field, value)
    s.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(s)
    return SiteSettingsOut.model_validate(s, from_attributes=True)


@router.get("/settings/public", response_model=SiteSettingsPublicOut)
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    """Public settings for CMS pages — no auth required."""
    s = await _get_or_create_settings(db)
    return SiteSettingsPublicOut(
        site_title=s.site_title,
        site_tagline=s.site_tagline,
        logo_url=s.logo_url,
        favicon_url=s.favicon_url,
        primary_color=s.primary_color,
        accent_color=s.accent_color,
        bg_color=s.bg_color,
        text_color=s.text_color,
        default_meta_title=s.default_meta_title,
        default_meta_description=s.default_meta_description,
        default_og_image=s.default_og_image,
        twitter_handle=s.twitter_handle,
        footer_text=s.footer_text,
        footer_links=s.footer_links,
        custom_css=s.custom_css,
        custom_head_html=s.custom_head_html,
        custom_footer_html=s.custom_footer_html,
        google_analytics_id=s.google_analytics_id,
        plausible_domain=s.plausible_domain,
    )
