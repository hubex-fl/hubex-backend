"""add execution run claim lease columns

Revision ID: e8f13c318a91
Revises: f6a7b8c9d0e1
Create Date: 2026-02-13 02:29:11.605282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f13c318a91'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("execution_runs", sa.Column("claimed_by", sa.String(length=96), nullable=True))
    op.add_column("execution_runs", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("execution_runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_execution_runs_status_lease_id",
        "execution_runs",
        ["status", "lease_expires_at", "id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_execution_runs_status_lease_id", table_name="execution_runs")
    op.drop_column("execution_runs", "lease_expires_at")
    op.drop_column("execution_runs", "claimed_at")
    op.drop_column("execution_runs", "claimed_by")
