"""add provider storage v1

Revision ID: b9c8d7e6f5a4
Revises: 43d03901379e
Create Date: 2026-02-12 14:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9c8d7e6f5a4"
down_revision: Union[str, Sequence[str], None] = "43d03901379e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("key", name="uq_provider_types_key"),
    )

    op.create_table(
        "provider_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_type_id", sa.Integer(), nullable=False),
        sa.Column("instance_key", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("config_ref", sa.String(length=256), nullable=True),
        sa.Column("secret_ref", sa.String(length=256), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_type_id"], ["provider_types.id"]),
        sa.UniqueConstraint("instance_key", name="uq_provider_instances_instance_key"),
    )
    op.create_index(
        "ix_provider_instances_provider_type_id", "provider_instances", ["provider_type_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_provider_instances_provider_type_id", table_name="provider_instances")
    op.drop_table("provider_instances")
    op.drop_table("provider_types")
