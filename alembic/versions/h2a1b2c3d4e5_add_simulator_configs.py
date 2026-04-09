"""add simulator_configs table

Revision ID: h2a1b2c3d4e5
Revises: h1_merge_heads
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

revision = "h2a1b2c3d4e5"
down_revision = "h1_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulator_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("org_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=True),
        sa.Column("device_uid", sa.String(128), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template", sa.String(50), nullable=True),
        sa.Column("variable_patterns", sa.JSON(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), server_default=sa.text("15"), nullable=False),
        sa.Column("speed_multiplier", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_virtual_device", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("total_points_sent", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_value_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_simulator_configs_owner_id", "simulator_configs", ["owner_id"])
    op.create_index("ix_simulator_configs_device_id", "simulator_configs", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_simulator_configs_device_id", table_name="simulator_configs")
    op.drop_index("ix_simulator_configs_owner_id", table_name="simulator_configs")
    op.drop_table("simulator_configs")
