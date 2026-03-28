"""Add display_hint/category to variable_definitions + variable_history table

Revision ID: c2d3e4f5g6h7
Revises: b1c2d3e4f5g6
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c2d3e4f5g6h7"
down_revision = "b1c2d3e4f5g6"
branch_labels = None
depends_on = None


def upgrade():
    # Add visualization columns to variable_definitions
    op.add_column(
        "variable_definitions",
        sa.Column("display_hint", sa.String(32), nullable=True),
    )
    op.add_column(
        "variable_definitions",
        sa.Column("category", sa.String(64), nullable=True),
    )

    # Create variable_history table
    op.create_table(
        "variable_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("variable_key", sa.String(128), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source", sa.String(16), server_default="system", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_variable_history_key_device_time",
        "variable_history",
        ["variable_key", "device_id", "recorded_at"],
    )
    op.create_index(
        "ix_variable_history_device_time",
        "variable_history",
        ["device_id", "recorded_at"],
    )


def downgrade():
    op.drop_index("ix_variable_history_device_time", table_name="variable_history")
    op.drop_index("ix_variable_history_key_device_time", table_name="variable_history")
    op.drop_table("variable_history")
    op.drop_column("variable_definitions", "category")
    op.drop_column("variable_definitions", "display_hint")
