"""add signals v1 storage

Revision ID: c8d1e4f6a7b2
Revises: b9c8d7e6f5a4
Create Date: 2026-02-12 17:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8d1e4f6a7b2"
down_revision: Union[str, Sequence[str], None] = "b9c8d7e6f5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signals_v1",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stream", sa.String(length=128), nullable=False),
        sa.Column("signal_type", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("provider_instance_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_instance_id"], ["provider_instances.id"]),
        sa.UniqueConstraint("idempotency_key", name="uq_signals_v1_idempotency_key"),
    )
    op.create_index("ix_signals_v1_stream", "signals_v1", ["stream"], unique=False)
    op.create_index("ix_signals_v1_provider_instance_id", "signals_v1", ["provider_instance_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_signals_v1_provider_instance_id", table_name="signals_v1")
    op.drop_index("ix_signals_v1_stream", table_name="signals_v1")
    op.drop_table("signals_v1")
