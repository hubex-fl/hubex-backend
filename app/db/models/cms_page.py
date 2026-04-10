"""CMS Page model — custom HTML/Markdown pages with template variables and sharing."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CmsPage(Base):
    __tablename__ = "cms_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_html: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    # "html" | "markdown" | "simple"
    content_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="html", server_default="html"
    )
    # "default" | "landing" | "minimal" | "fullscreen"
    layout: Mapped[str] = mapped_column(
        String(32), nullable=False, default="default", server_default="default"
    )
    meta_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_image: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Sharing
    # "private" | "public" | "embed"
    visibility: Mapped[str] = mapped_column(
        String(16), nullable=False, default="private", server_default="private"
    )
    public_token: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    public_pin: Mapped[str | None] = mapped_column(String(16), nullable=True)
    embed_allowed_origins: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Status
    published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
