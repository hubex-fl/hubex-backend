"""Retrofit Device Profiles — pre-built configs for existing smart devices and industrial equipment."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeviceProfile(Base):
    """Pre-built device profile for retrofit/smart device integration."""
    __tablename__ = "device_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # energy_meter, inverter, sensor, smart_switch, plc
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)  # modbus_rtu, modbus_tcp, mqtt, rest_api, canbus, ir
    # Connection config template
    connection_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Register/topic/endpoint mappings → variables
    register_map: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{register: 0x0000, type: "holding", data_type: "uint16", scale: 0.1, variable_key: "voltage", semantic_type: "voltage", unit: "V"}]
    writable_registers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="community")  # community, verified, official
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
