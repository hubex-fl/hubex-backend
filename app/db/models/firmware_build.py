"""Firmware build job tracking (Sprint 4 — firmware_builder).

One row per build request. The actual compile happens in an ephemeral
Portainer-managed sidecar container (see ``app/core/firmware_builder.py``);
this table just tracks queue state, logs, and the final artifact bytes
for later download / OTA push.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FirmwareBuild(Base):
    __tablename__ = "firmware_builds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Who kicked the build off
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Optional device binding (for OTA target). Nullable so you can build
    # a firmware against a board profile without owning a device yet.
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Required: which board profile to target
    board_profile_id: Mapped[int] = mapped_column(
        ForeignKey("board_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # PlatformIO environment name (e.g. "esp32dev"). Derived from the board.
    pio_env: Mapped[str] = mapped_column(String(64), nullable=False, default="esp32dev")
    # Status state machine: queued → building → (success | failed | cancelled)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    # Sidecar container name (for diagnostics + mid-build cancel)
    container_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Append-only build logs. Text to allow arbitrary length; capped at
    # ~64kb in the worker to keep the DB row reasonable.
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The compiled .bin bytes. NULL until status=success. Small enough for
    # an ESP32 firmware (max ~1.5MB per partition).
    artifact_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    artifact_size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_filename: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Structured error code on failure (e.g. "PIO_COMPILE_FAILED",
    # "PORTAINER_UNREACHABLE", "BOARD_NOT_SUPPORTED")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Sprint 7 — link to the OTA rollout created when the user pushes
    # this build to a device. NULL = never promoted (just a downloadable
    # artifact). Setting this field creates a FirmwareVersion +
    # OtaRollout + DeviceOtaStatus in one atomic step via the
    # `/firmware/builds/{id}/ota` endpoint — see app/api/v1/firmware.py.
    ota_rollout_id: Mapped[int | None] = mapped_column(
        ForeignKey("ota_rollouts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
