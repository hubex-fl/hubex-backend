"""add variable snapshots and applied acks

Revision ID: 38d3f3fd4244
Revises: af7caca26c62
Create Date: 2025-12-22 01:45:57.437508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38d3f3fd4244'
down_revision: Union[str, Sequence[str], None] = 'af7caca26c62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "variable_snapshots",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_version", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_variable_snapshots_device_id",
        "variable_snapshots",
        ["device_id"],
        unique=False,
    )
    op.create_index(
        "ix_variable_snapshots_resolved_at",
        "variable_snapshots",
        ["resolved_at"],
        unique=False,
    )

    op.create_table(
        "variable_snapshot_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(length=40),
            sa.ForeignKey("variable_snapshots.id"),
            nullable=False,
        ),
        sa.Column("variable_key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("masked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_secret", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("precedence", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("resolved_type", sa.String(length=16), nullable=True),
        sa.Column("constraints", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_variable_snapshot_items_snapshot_id",
        "variable_snapshot_items",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_variable_snapshot_items_key",
        "variable_snapshot_items",
        ["variable_key"],
        unique=False,
    )

    op.create_table(
        "variable_applied_acks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(length=40),
            sa.ForeignKey("variable_snapshots.id"),
            nullable=False,
        ),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("variable_key", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "device_id",
            "variable_key",
            "version",
            name="uq_variable_applied_ack",
        ),
    )
    op.create_index(
        "ix_variable_applied_snapshot",
        "variable_applied_acks",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_variable_applied_device",
        "variable_applied_acks",
        ["device_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_variable_applied_device", table_name="variable_applied_acks")
    op.drop_index("ix_variable_applied_snapshot", table_name="variable_applied_acks")
    op.drop_table("variable_applied_acks")
    op.drop_index("ix_variable_snapshot_items_key", table_name="variable_snapshot_items")
    op.drop_index(
        "ix_variable_snapshot_items_snapshot_id", table_name="variable_snapshot_items"
    )
    op.drop_table("variable_snapshot_items")
    op.drop_index("ix_variable_snapshots_resolved_at", table_name="variable_snapshots")
    op.drop_index("ix_variable_snapshots_device_id", table_name="variable_snapshots")
    op.drop_table("variable_snapshots")
