"""Add tenant webhook_api_key

Revision ID: 003_tenant_webhook
Revises: 002_multi_tenant
Create Date: 2026-03-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_tenant_webhook'
down_revision: Union[str, None] = '002_multi_tenant'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 在 tenants 表添加 webhook_api_key 字段
    op.add_column('tenants', sa.Column('webhook_api_key', sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column('tenants', 'webhook_api_key')
