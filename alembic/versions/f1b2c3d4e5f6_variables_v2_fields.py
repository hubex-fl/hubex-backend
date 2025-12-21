from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f1b2c3d4e5f6"
down_revision = "b7c2f1a9e4c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("variable_definitions", sa.Column("unit", sa.String(length=32), nullable=True))
    op.add_column("variable_definitions", sa.Column("min_value", sa.Float(), nullable=True))
    op.add_column("variable_definitions", sa.Column("max_value", sa.Float(), nullable=True))
    op.add_column("variable_definitions", sa.Column("enum_values", sa.JSON(), nullable=True))
    op.add_column("variable_definitions", sa.Column("regex", sa.String(length=256), nullable=True))
    op.add_column("variable_definitions", sa.Column("user_writable", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("variable_definitions", sa.Column("device_writable", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("variable_definitions", sa.Column("allow_device_override", sa.Boolean(), server_default=sa.text("true"), nullable=False))

    op.add_column("variable_values", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_variable_values_user_id", "variable_values", ["user_id"])

    op.drop_constraint("uq_variable_values_key_device_scope", "variable_values", type_="unique")
    op.create_unique_constraint(
        "uq_variable_values_key_device_scope",
        "variable_values",
        ["variable_key", "device_id", "scope", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_variable_values_key_device_scope", "variable_values", type_="unique")
    op.create_unique_constraint(
        "uq_variable_values_key_device_scope",
        "variable_values",
        ["variable_key", "device_id", "scope"],
    )
    op.drop_index("ix_variable_values_user_id", table_name="variable_values")
    op.drop_column("variable_values", "user_id")

    op.drop_column("variable_definitions", "allow_device_override")
    op.drop_column("variable_definitions", "device_writable")
    op.drop_column("variable_definitions", "user_writable")
    op.drop_column("variable_definitions", "regex")
    op.drop_column("variable_definitions", "enum_values")
    op.drop_column("variable_definitions", "max_value")
    op.drop_column("variable_definitions", "min_value")
    op.drop_column("variable_definitions", "unit")
