"""add execution storage foundation

Revision ID: f6a7b8c9d0e1
Revises: e4f1a2b3c4d5
Create Date: 2026-02-12 17:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e4f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("key", name="uq_execution_definitions_key"),
    )

    op.create_table(
        "execution_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("definition_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["definition_id"], ["execution_definitions.id"]),
        sa.UniqueConstraint(
            "definition_id",
            "idempotency_key",
            name="uq_execution_runs_definition_id_idempotency_key",
        ),
    )
    op.create_index(
        "ix_execution_runs_definition_id_id",
        "execution_runs",
        ["definition_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_execution_runs_definition_id_id", table_name="execution_runs")
    op.drop_table("execution_runs")
    op.drop_table("execution_definitions")

