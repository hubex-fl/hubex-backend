"""Hardware Abstraction Layer — Board profiles, shields, and pin configurations."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BoardProfile(Base):
    """Hardware board profile with chip specs and pin capabilities."""
    __tablename__ = "board_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    chip: Mapped[str] = mapped_column(String(32), nullable=False)  # esp32, esp32s3, esp32c3, atmega328, rp2040
    pins: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Each pin: {number, label, capabilities: [digital_io, adc, pwm, i2c_sda, i2c_scl, spi, uart_tx, uart_rx, dac, touch]}
    flash_size_kb: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    ram_size_kb: Mapped[int] = mapped_column(Integer, nullable=False, default=520)
    wifi_capable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    bluetooth_capable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShieldProfile(Base):
    """Shield/Hat definitions that attach to a board and occupy pins."""
    __tablename__ = "shield_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_chip: Mapped[str | None] = mapped_column(String(32), nullable=True)  # null = universal
    occupied_pins: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # pin numbers taken
    exposed_pins: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # pin numbers passed through
    bus_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # serial, spi, i2c
    components: Mapped[list | None] = mapped_column(JSON, nullable=True)  # sensors/actuators on the shield
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PinConfiguration(Base):
    """Per-device pin assignment — what function each pin serves."""
    __tablename__ = "pin_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    board_profile_id: Mapped[int] = mapped_column(
        ForeignKey("board_profiles.id", ondelete="SET NULL"), nullable=True
    )
    shield_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("shield_profiles.id", ondelete="SET NULL"), nullable=True
    )
    pin_assignments: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # {pin_number: {function: "sensor_input", component: "dht22", variable_key: "temperature"}}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
