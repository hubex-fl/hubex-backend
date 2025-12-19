"""add execution_contexts and tasks

Revision ID: c3b0f8d9a1e2
Revises: 9f8c2b3f1a2d
Create Date: 2025-12-19 04:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3b0f8d9a1e2"
down_revision: Union[str, Sequence[str], None] = "9f8c2b3f1a2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "execution_contexts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("context_key", sa.String(length=128), nullable=False),
        sa.Column(
            "capabilities",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("client_id", "context_key", name="uq_execution_context_client_key"),
    )
    op.create_index(
        "ix_execution_contexts_client_last_seen",
        "execution_contexts",
        ["client_id", "last_seen_at"],
        unique=False,
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column(
            "execution_context_id",
            sa.Integer(),
            sa.ForeignKey("execution_contexts.id"),
            nullable=True,
        ),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_tasks_client_status_priority_created",
        "tasks",
        ["client_id", "status", "priority", "created_at"],
        unique=False,
    )
    op.create_index("ix_tasks_lease_expires_at", "tasks", ["lease_expires_at"], unique=False)
    op.create_index(
        "uq_tasks_client_idempotency",
        "tasks",
        ["client_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_tasks_client_idempotency", table_name="tasks")
    op.drop_index("ix_tasks_lease_expires_at", table_name="tasks")
    op.drop_index("ix_tasks_client_status_priority_created", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_execution_contexts_client_last_seen", table_name="execution_contexts")
    op.drop_table("execution_contexts")
