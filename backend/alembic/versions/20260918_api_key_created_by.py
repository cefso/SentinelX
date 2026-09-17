"""api_keys.created_by 溯源字段

Revision ID: 20260918_api_key_created_by
Revises: 20260918_alert_indexes
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa

revision = "20260918_api_key_created_by"
down_revision = "20260918_alert_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("created_by", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "created_by")
