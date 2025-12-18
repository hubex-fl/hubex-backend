"""add user_id to pairing_sessions

Revision ID: 7b9f1e2a3c4d
Revises: 46afa1a7adce
Create Date: 2025-12-18 06:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b9f1e2a3c4d"
down_revision: Union[str, Sequence[str], None] = "46afa1a7adce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("pairing_sessions", sa.Column("user_id", sa.Integer(), nullable=True))
    op.execute("DELETE FROM pairing_sessions")
    op.alter_column("pairing_sessions", "user_id", nullable=False)
    op.create_index(op.f("ix_pairing_sessions_user_id"), "pairing_sessions", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_pairing_sessions_user_id_users",
        "pairing_sessions",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_pairing_sessions_user_id_users", "pairing_sessions", type_="foreignkey")
    op.drop_index(op.f("ix_pairing_sessions_user_id"), table_name="pairing_sessions")
    op.drop_column("pairing_sessions", "user_id")
