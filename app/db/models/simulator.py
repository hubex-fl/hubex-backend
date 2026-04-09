from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Integer,
    Float,
    Text,
    func,
    text,
)

from app.db.base import Base

try:
    from sqlalchemy.dialects.postgresql import JSONB as _JSON_TYPE
except Exception:
    from sqlalchemy import JSON as _JSON_TYPE


class SimulatorConfig(Base):
    __tablename__ = "simulator_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Link to a real device (virtual or existing)
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=True
    )
    device_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Variable patterns: JSON array
    # [{"variable_key": "temperature", "pattern": "sine", "config": {...}}, ...]
    variable_patterns: Mapped[list] = mapped_column(
        _JSON_TYPE, nullable=False, default=list
    )

    # Runtime config
    interval_seconds: Mapped[int] = mapped_column(
        Integer, server_default=text("15"), nullable=False
    )
    speed_multiplier: Mapped[float] = mapped_column(
        Float, server_default=text("1.0"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    is_virtual_device: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )

    # Stats
    total_points_sent: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    started_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_value_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
