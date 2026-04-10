"""Plugin system models — manifest, registry, and execution tracking."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False, default="0.1.0")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Manifest: capabilities required, hooks, config schema
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Capability gating: which caps does the plugin need
    required_caps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Sandbox config
    sandbox_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="restricted")
    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    installed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Sprint 3 — Service vs Connector plugins
    # "service"  = Docker container managed via Portainer (requires orchestrator feature)
    # "connector" = API credentials only, no infra cost
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="connector")
    # Runtime lifecycle state for service plugins:
    # None (not a service / never installed) | "installing" | "running" | "stopped" |
    # "unhealthy" | "error". Connector plugins leave this NULL.
    runtime_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Portainer container name for service plugins. NULL for connector plugins.
    container_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
