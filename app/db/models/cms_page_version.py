"""CMS Page version history — snapshots created on every update."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CmsPageVersion(Base):
    __tablename__ = "cms_page_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(
        ForeignKey("cms_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    blocks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
