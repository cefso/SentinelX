"""Add user approval fields

Revision ID: 004_add_user_approval
Revises: 003_tenant_webhook
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_user_approval'
down_revision: Union[str, None] = '003_tenant_webhook'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users 表添加审批相关字段
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('users', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('approved_by', sa.Integer(), nullable=True))

    # UserTenants 表添加 is_primary 字段
    op.add_column('user_tenants', sa.Column('is_primary', sa.Boolean(), nullable=True, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('user_tenants', 'is_primary')
    op.drop_column('users', 'approved_by')
    op.drop_column('users', 'approved_at')
    op.drop_column('users', 'is_approved')
