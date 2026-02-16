from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModuleRegistry(Base):
    __tablename__ = "module_registry"

    key: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
