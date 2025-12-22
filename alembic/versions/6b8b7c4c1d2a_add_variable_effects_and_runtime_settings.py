"""add variable effects and device runtime settings

Revision ID: 6b8b7c4c1d2a
Revises: 38d3f3fd4244
Create Date: 2025-12-22 05:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b8b7c4c1d2a"
down_revision: Union[str, Sequence[str], None] = "38d3f3fd4244"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_runtime_settings",
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), primary_key=True),
        sa.Column("telemetry_interval_ms", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_device_runtime_settings_device_id",
        "device_runtime_settings",
        ["device_id"],
        unique=False,
    )

    op.create_table(
        "variable_effects",
        sa.Column("id", sa.String(length=36), primary_key=True),
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
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("device_uid", sa.String(length=64), nullable=True),
        sa.Column(
            "trigger_audit_id",
            sa.Integer(),
            sa.ForeignKey("variable_audits.id"),
            nullable=True,
        ),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_variable_effects_status_next",
        "variable_effects",
        ["status", "next_attempt_at"],
        unique=False,
    )
    op.create_index(
        "ix_variable_effects_device_id",
        "variable_effects",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_variable_effects_correlation",
        "variable_effects",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_variable_effects_audit",
        "variable_effects",
        ["trigger_audit_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_variable_effects_audit", table_name="variable_effects")
    op.drop_index("ix_variable_effects_correlation", table_name="variable_effects")
    op.drop_index("ix_variable_effects_device_id", table_name="variable_effects")
    op.drop_index("ix_variable_effects_status_next", table_name="variable_effects")
    op.drop_table("variable_effects")
    op.drop_index("ix_device_runtime_settings_device_id", table_name="device_runtime_settings")
    op.drop_table("device_runtime_settings")
