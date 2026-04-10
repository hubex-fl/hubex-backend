from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeatureFlag(Base):
    """Runtime feature flag (global / single-tenant).

    Each flag corresponds to an entry in ``FEATURES`` (``app/core/features.py``).
    The registry is the source of truth for existence + defaults; this table
    persists user overrides across restarts.
    """

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(96), primary_key=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
