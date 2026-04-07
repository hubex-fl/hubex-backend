"""Custom API Endpoint model — user-defined REST endpoints that query HUBEX data."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomEndpoint(Base):
    __tablename__ = "custom_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    route_path: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    method: Mapped[str] = mapped_column(String(8), nullable=False, default="GET")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Response mapping: which data sources to query and how to format
    response_mapping: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Query parameters definition
    params_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Rate limiting per endpoint
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    # Auth: which API key scopes can access this endpoint
    required_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Traffic stats
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
