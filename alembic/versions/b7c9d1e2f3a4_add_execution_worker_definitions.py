"""add execution worker definitions

Revision ID: b7c9d1e2f3a4
Revises: e8f13c318a91
Create Date: 2026-02-13 03:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c9d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "e8f13c318a91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "execution_worker_defs",
        sa.Column("worker_id", sa.String(length=96), nullable=False),
        sa.Column("definition_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["worker_id"], ["execution_workers.id"]),
        sa.ForeignKeyConstraint(["definition_id"], ["execution_definitions.id"]),
        sa.PrimaryKeyConstraint("worker_id", "definition_id"),
    )
    op.create_index(
        "ix_execution_worker_defs_definition_worker",
        "execution_worker_defs",
        ["definition_id", "worker_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_execution_worker_defs_definition_worker", table_name="execution_worker_defs")
    op.drop_table("execution_worker_defs")
