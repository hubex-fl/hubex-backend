"""add execution worker registry

Revision ID: 801faeb5bf4b
Revises: 62b2680a06dd
Create Date: 2026-02-13 15:53:56.823676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '801faeb5bf4b'
down_revision: Union[str, Sequence[str], None] = '62b2680a06dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "execution_workers",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_execution_workers_last_seen_at", "execution_workers", ["last_seen_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_execution_workers_last_seen_at", table_name="execution_workers")
    op.drop_table("execution_workers")
