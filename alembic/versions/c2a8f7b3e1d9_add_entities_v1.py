from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c2a8f7b3e1d9"
down_revision = "af7caca26c62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("entity_id", sa.String(length=64), primary_key=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("health_last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("health_status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_entities_type", "entities", ["type"])

    op.create_table(
        "entity_device_bindings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.String(length=64), sa.ForeignKey("entities.entity_id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_entity_device_bindings_entity_id", "entity_device_bindings", ["entity_id"])
    op.create_index("ix_entity_device_bindings_device_id", "entity_device_bindings", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_entity_device_bindings_device_id", table_name="entity_device_bindings")
    op.drop_index("ix_entity_device_bindings_entity_id", table_name="entity_device_bindings")
    op.drop_table("entity_device_bindings")
    op.drop_index("ix_entities_type", table_name="entities")
    op.drop_table("entities")
