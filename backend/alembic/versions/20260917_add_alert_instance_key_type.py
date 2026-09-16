"""add alerts.instance_key / alert_type for by-instance aggregation

Revision ID: 20260917_instance_key_type
Revises: 20260916_tenant_id_int
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260917_instance_key_type"
down_revision = "20260916_tenant_id_int"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("instance_key", sa.String(256), nullable=True))
    op.add_column("alerts", sa.Column("alert_type", sa.String(32), nullable=True))
    op.create_index(
        "idx_alerts_tenant_instance_key",
        "alerts",
        ["tenant_id", "instance_key"],
    )
    op.create_index(
        "idx_alerts_by_instance_detail",
        "alerts",
        ["tenant_id", "instance_key", "alert_type", "fired_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_alerts_by_instance_detail", table_name="alerts")
    op.drop_index("idx_alerts_tenant_instance_key", table_name="alerts")
    op.drop_column("alerts", "alert_type")
    op.drop_column("alerts", "instance_key")
