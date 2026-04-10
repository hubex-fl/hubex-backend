"""CMS Menu model — navigation menus composed of pages, links, sections, dividers."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CmsMenu(Base):
    __tablename__ = "cms_menus"
    __table_args__ = (
        UniqueConstraint("owner_id", "location", name="uq_cms_menus_owner_location"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Menu slot: "header" | "footer" | "sidebar" | custom string
    location: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Nested array of menu items; see CmsMenuItem schema for format
    items: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
