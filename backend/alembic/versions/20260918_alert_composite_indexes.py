"""alerts composite indexes + drop useless JSON B-tree index

- create idx_alerts_tenant_status_fired (tenant_id, status, fired_at)
- drop idx_alerts_labels (B-tree on JSON labels is not useful; keep GIN)
- create idx_alert_history_tenant_created (tenant_id, created_at)

Revision ID: 20260918_alert_indexes
Revises: 20260917_instance_key_type
Create Date: 2026-09-18
"""
from alembic import op

revision = "20260918_alert_indexes"
down_revision = "20260917_instance_key_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_alerts_tenant_status_fired",
        "alerts",
        ["tenant_id", "status", "fired_at"],
    )
    op.drop_index("idx_alerts_labels", table_name="alerts")
    op.create_index(
        "idx_alert_history_tenant_created",
        "alert_history",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_alert_history_tenant_created", table_name="alert_history")
    op.create_index("idx_alerts_labels", "alerts", ["tenant_id", "labels"])
    op.drop_index("idx_alerts_tenant_status_fired", table_name="alerts")
