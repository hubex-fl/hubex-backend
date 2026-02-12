from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProviderType(Base):
    __tablename__ = "provider_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    instances: Mapped[list["ProviderInstance"]] = relationship(
        "ProviderInstance", back_populates="provider_type", lazy="selectin"
    )


class ProviderInstance(Base):
    __tablename__ = "provider_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_type_id: Mapped[int] = mapped_column(ForeignKey("provider_types.id"), index=True, nullable=False)
    instance_key: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    provider_type: Mapped[ProviderType] = relationship("ProviderType", back_populates="instances", lazy="joined")
