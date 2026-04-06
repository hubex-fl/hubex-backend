"""Component Library — sensor, actuator, and module manifests."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HardwareComponent(Base):
    """A hardware component manifest (sensor, actuator, display, module)."""
    __tablename__ = "hardware_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)  # sensor, actuator, display, module
    # Pin requirements
    pin_requirements: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{type: "digital_io", count: 1, label: "Data"}, {type: "i2c", count: 2}]
    bus_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # i2c, spi, uart, onewire
    # Libraries needed for Arduino/PlatformIO
    libraries_required: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Code template (Arduino C++)
    code_template: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    # Output variables (what this component produces/accepts)
    variables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{key: "temperature", semantic_type: "temperature", direction: "read", unit: "°C"}]
    # Default visualization widget type
    default_widget: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    datasheet_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
