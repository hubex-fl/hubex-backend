"""AutomationRule and AutomationFireLog models."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB as _JSON_TYPE
except Exception:
    from sqlalchemy import JSON as _JSON_TYPE


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Trigger
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(_JSON_TYPE, nullable=False, default=dict)

    # Action
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    action_config: Mapped[dict] = mapped_column(_JSON_TYPE, nullable=False, default=dict)

    # Cooldown / tracking
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300, server_default="300")
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fire_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AutomationStep(Base):
    """Individual step in a multi-step automation chain."""
    __tablename__ = "automation_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    action_config: Mapped[dict] = mapped_column(_JSON_TYPE, nullable=False, default=dict)
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    condition_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "branch", None
    condition_config: Mapped[dict | None] = mapped_column(_JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AutomationFireLog(Base):
    __tablename__ = "automation_fire_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    context_json: Mapped[dict] = mapped_column(_JSON_TYPE, nullable=False, default=dict)
