"""add effects v1 storage

Revision ID: a7b8c9d0e1f2
Revises: c1d2e3f4a5b6
Create Date: 2026-01-02 21:26:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "effects_v1",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("effect_id", sa.String(length=64), nullable=False),
        sa.Column("source_event_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("effect_id", name="uq_effects_v1_effect_id"),
    )
    op.create_index("ix_effects_v1_created_at", "effects_v1", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_effects_v1_created_at", table_name="effects_v1")
    op.drop_table("effects_v1")
