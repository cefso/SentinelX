"""alert aggregate parent/group fields

Revision ID: 20260605_agg_fields
Revises: 20260412_consolidated_initial_schema
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "20260605_agg_fields"
down_revision = "consolidated_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("aggregate_parent_id", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("aggregate_group_id", sa.Integer(), nullable=True))
    op.create_index("ix_alerts_aggregate_parent_id", "alerts", ["aggregate_parent_id"])
    op.create_index("ix_alerts_aggregate_group_id", "alerts", ["aggregate_group_id"])
    op.create_foreign_key(
        "fk_alerts_aggregate_group_id",
        "alerts",
        "alert_aggregate_groups",
        ["aggregate_group_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_alerts_aggregate_group_id", "alerts", type_="foreignkey")
    op.drop_index("ix_alerts_aggregate_group_id", table_name="alerts")
    op.drop_index("ix_alerts_aggregate_parent_id", table_name="alerts")
    op.drop_column("alerts", "aggregate_group_id")
    op.drop_column("alerts", "aggregate_parent_id")
