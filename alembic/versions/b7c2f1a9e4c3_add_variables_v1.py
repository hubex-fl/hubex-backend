from alembic import op
import sqlalchemy as sa

try:
    from sqlalchemy.dialects import postgresql
    JSON_TYPE = postgresql.JSONB
except Exception:
    JSON_TYPE = sa.JSON


# revision identifiers, used by Alembic.
revision = "b7c2f1a9e4c3"
down_revision = "f4d1c2b9e8a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "variable_definitions",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("value_type", sa.String(length=16), nullable=False),
        sa.Column("default_value", JSON_TYPE, nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_secret", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_readonly", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_variable_definitions_scope", "variable_definitions", ["scope"]
    )

    op.create_table(
        "variable_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "variable_key",
            sa.String(length=128),
            sa.ForeignKey("variable_definitions.key"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("value_json", JSON_TYPE, nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.UniqueConstraint(
            "variable_key",
            "device_id",
            "scope",
            name="uq_variable_values_key_device_scope",
        ),
    )
    op.create_index(
        "ix_variable_values_variable_key", "variable_values", ["variable_key"]
    )
    op.create_index(
        "ix_variable_values_device_id", "variable_values", ["device_id"]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.create_index(
            "uq_variable_values_global_key",
            "variable_values",
            ["variable_key"],
            unique=True,
            postgresql_where=sa.text("device_id IS NULL AND scope = 'global'"),
        )

    op.create_table(
        "variable_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("variable_key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("old_value_json", JSON_TYPE, nullable=True),
        sa.Column("new_value_json", JSON_TYPE, nullable=True),
        sa.Column("old_version", sa.Integer(), nullable=True),
        sa.Column("new_version", sa.Integer(), nullable=True),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_variable_audits_key_created", "variable_audits", ["variable_key", "created_at"]
    )
    op.create_index("ix_variable_audits_device", "variable_audits", ["device_id"])


def downgrade():
    op.drop_index("ix_variable_audits_device", table_name="variable_audits")
    op.drop_index("ix_variable_audits_key_created", table_name="variable_audits")
    op.drop_table("variable_audits")

    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("uq_variable_values_global_key", table_name="variable_values")
    op.drop_index("ix_variable_values_device_id", table_name="variable_values")
    op.drop_index("ix_variable_values_variable_key", table_name="variable_values")
    op.drop_table("variable_values")

    op.drop_index("ix_variable_definitions_scope", table_name="variable_definitions")
    op.drop_table("variable_definitions")
