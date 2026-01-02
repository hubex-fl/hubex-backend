"""add audit v1 storage

Revision ID: f3c1a0b4d2e6
Revises: e1a4b2c7d9f0
Create Date: 2026-01-02 20:52:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3c1a0b4d2e6"
down_revision = "e1a4b2c7d9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_v1_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource", sa.String(length=256), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_audit_v1_entries_action", "audit_v1_entries", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_v1_entries_action", table_name="audit_v1_entries")
    op.drop_table("audit_v1_entries")
