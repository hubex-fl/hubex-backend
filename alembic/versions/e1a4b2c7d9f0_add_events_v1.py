"""add events v1 storage

Revision ID: e1a4b2c7d9f0
Revises: d4f0a2b6c9e1
Create Date: 2026-01-02 20:48:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e1a4b2c7d9f0"
down_revision = "d4f0a2b6c9e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events_v1",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stream", sa.String(length=128), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_events_v1_stream", "events_v1", ["stream"])

    op.create_table(
        "events_v1_checkpoints",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stream", sa.String(length=128), nullable=False),
        sa.Column("subscriber_id", sa.String(length=128), nullable=False),
        sa.Column("cursor", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_events_v1_checkpoints_stream", "events_v1_checkpoints", ["stream"]
    )
    op.create_index(
        "ix_events_v1_checkpoints_subscriber_id",
        "events_v1_checkpoints",
        ["subscriber_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_events_v1_checkpoints_subscriber_id", table_name="events_v1_checkpoints")
    op.drop_index("ix_events_v1_checkpoints_stream", table_name="events_v1_checkpoints")
    op.drop_table("events_v1_checkpoints")
    op.drop_index("ix_events_v1_stream", table_name="events_v1")
    op.drop_table("events_v1")
