"""Site Settings model — global branding, SEO, analytics, footer settings."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SiteSettings(Base):
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Branding
    site_title: Mapped[str] = mapped_column(String(256), nullable=False, default="HUBEX", server_default="HUBEX")
    site_tagline: Mapped[str | None] = mapped_column(String(512), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    primary_color: Mapped[str] = mapped_column(
        String(16), nullable=False, default="#F5A623", server_default="#F5A623"
    )
    accent_color: Mapped[str] = mapped_column(
        String(16), nullable=False, default="#2DD4BF", server_default="#2DD4BF"
    )
    bg_color: Mapped[str] = mapped_column(
        String(16), nullable=False, default="#111110", server_default="#111110"
    )
    text_color: Mapped[str] = mapped_column(
        String(16), nullable=False, default="#E5E5E5", server_default="#E5E5E5"
    )

    # SEO defaults
    default_meta_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    default_meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_og_image: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    twitter_handle: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Analytics
    google_analytics_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plausible_domain: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Footer
    footer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    footer_links: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Custom
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_head_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_footer_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
