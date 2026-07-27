"""webhook logs table

Revision ID: 20260724_webhook_logs
Revises: 20260605_agg_fields
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260724_webhook_logs"
down_revision = "20260605_agg_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("client_id", sa.String(length=32), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("is_dismissed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_logs_id", "webhook_logs", ["id"], unique=False)
    op.create_index("ix_webhook_logs_tenant_id", "webhook_logs", ["tenant_id"], unique=False)
    op.create_index("ix_webhook_logs_created_at", "webhook_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_webhook_logs_created_at", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_tenant_id", table_name="webhook_logs")
    op.drop_index("ix_webhook_logs_id", table_name="webhook_logs")
    op.drop_table("webhook_logs")
