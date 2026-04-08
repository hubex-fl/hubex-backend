"""Custom API Endpoint model — user-defined REST endpoints that query HUBEX data."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomEndpoint(Base):
    __tablename__ = "custom_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Endpoint definition
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Data source configuration (JSON)
    # For GET: { type, variable_keys, device_uids, entity_ids, aggregation, time_range, group_by, format }
    # For POST: { type: "set_variable", allowed_variable_keys, device_uid }
    source_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Security
    auth_type: Mapped[str] = mapped_column(String(20), nullable=False, default="api_key")
    api_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    write_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Traffic stats
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
