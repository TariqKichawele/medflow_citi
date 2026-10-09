import sqlalchemy as sa
from alembic import op

revision = "0003_roles"
down_revision = "0002_list_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("role_id", "permission", name="uq_role_permissions_role_permission"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    from app.permissions import BUILTIN_ROLES

    bind = op.get_bind()
    for name, spec in BUILTIN_ROLES.items():
        bind.execute(
            sa.text("INSERT INTO roles (name, description) VALUES (:name, :description)"),
            {"name": name, "description": spec.description},
        )
        role_id = bind.execute(
            sa.text("SELECT id FROM roles WHERE name = :name"),
            {"name": name},
        ).scalar_one()
        for permission in sorted(item.value for item in spec.permissions):
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission) VALUES (:role_id, :permission)"
                ),
                {"role_id": role_id, "permission": permission},
            )


def downgrade() -> None:
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_table("roles")
