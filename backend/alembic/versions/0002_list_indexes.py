from alembic import op

revision = "0002_list_indexes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_equipment_facility_id", "equipment", ["facility_id"])
    op.create_index("ix_work_orders_equipment_id", "work_orders", ["equipment_id"])
    op.create_index("ix_work_orders_technician_id", "work_orders", ["technician_id"])


def downgrade() -> None:
    op.drop_index("ix_work_orders_technician_id", table_name="work_orders")
    op.drop_index("ix_work_orders_equipment_id", table_name="work_orders")
    op.drop_index("ix_equipment_facility_id", table_name="equipment")
