"""add automation_steps table for multi-step chains

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects.postgresql import JSONB
except ImportError:
    JSONB = sa.JSON

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_steps",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "rule_id",
            sa.Integer,
            sa.ForeignKey("automation_rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("action_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("delay_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("condition_type", sa.String(20), nullable=True),
        sa.Column("condition_config", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("automation_steps")
