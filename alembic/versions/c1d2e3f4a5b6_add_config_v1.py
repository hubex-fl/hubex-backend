"""add config v1 storage

Revision ID: c1d2e3f4a5b6
Revises: b5a9c7d1e2f3
Create Date: 2026-01-02 21:12:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "b5a9c7d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_v1",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("namespace", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=256), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("namespace", "key", name="uq_config_v1_namespace_key"),
    )
    op.create_index("ix_config_v1_namespace", "config_v1", ["namespace"])
    op.create_index("ix_config_v1_namespace_key", "config_v1", ["namespace", "key"])


def downgrade() -> None:
    op.drop_index("ix_config_v1_namespace_key", table_name="config_v1")
    op.drop_index("ix_config_v1_namespace", table_name="config_v1")
    op.drop_table("config_v1")
