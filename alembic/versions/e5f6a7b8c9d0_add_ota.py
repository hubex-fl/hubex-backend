"""add OTA: firmware_versions, ota_rollouts, device_ota_status

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. firmware_versions
    op.create_table(
        "firmware_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("binary_url", sa.String(512), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column("min_hw_version", sa.String(64), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_firmware_versions_version"),
    )
    op.create_index("ix_firmware_versions_version", "firmware_versions", ["version"])
    op.create_index("ix_firmware_versions_org_id", "firmware_versions", ["org_id"])

    # 2. ota_rollouts
    op.create_table(
        "ota_rollouts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("firmware_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("strategy", sa.String(16), nullable=False),
        sa.Column("target_filter", sa.JSON(), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["firmware_id"], ["firmware_versions.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ota_rollouts_firmware_id", "ota_rollouts", ["firmware_id"])
    op.create_index("ix_ota_rollouts_org_id", "ota_rollouts", ["org_id"])

    # 3. device_ota_status
    op.create_table(
        "device_ota_status",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("rollout_id", sa.Integer(), nullable=False),
        sa.Column("firmware_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["firmware_id"], ["firmware_versions.id"]),
        sa.ForeignKeyConstraint(["rollout_id"], ["ota_rollouts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "rollout_id", name="uq_device_rollout"),
    )
    op.create_index("ix_device_ota_status_device_id", "device_ota_status", ["device_id"])
    op.create_index("ix_device_ota_status_rollout_id", "device_ota_status", ["rollout_id"])


def downgrade() -> None:
    op.drop_table("device_ota_status")
    op.drop_table("ota_rollouts")
    op.drop_table("firmware_versions")
