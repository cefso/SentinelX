"""add alert aggregate tables

Revision ID: 012_add_aggregate_tables
Revises: 011_add_cloud_metric_i18n_fields
Create Date: 2026-04-08 08:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_add_aggregate_tables'
down_revision: Union[str, None] = '011_add_cloud_metric_i18n_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'alert_aggregate_groups',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('group_key', sa.String(256), nullable=False, index=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('alert_rules.id'), nullable=True),
        sa.Column('alert_count', sa.Integer(), default=1),
        sa.Column('fired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_alert_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'alert_aggregate_members',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('alert_aggregate_groups.id'), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False, index=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('alert_aggregate_members')
    op.drop_table('alert_aggregate_groups')
