"""add secrets v1 storage

Revision ID: b5a9c7d1e2f3
Revises: f3c1a0b4d2e6
Create Date: 2026-01-02 21:02:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b5a9c7d1e2f3"
down_revision = "f3c1a0b4d2e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "secrets_v1",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("namespace", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("namespace", "key", name="uq_secrets_v1_namespace_key"),
    )


def downgrade() -> None:
    op.drop_table("secrets_v1")
