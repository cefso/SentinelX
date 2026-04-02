"""Add client_id to alert_sources

Revision ID: 005_client_id
Revises: 004_add_user_approval
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_client_id'
down_revision: Union[str, None] = '004_add_user_approval'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 先添加可空列
    op.add_column(
        'alert_sources',
        sa.Column('client_id', sa.String(32), nullable=True, unique=True, index=True)
    )
    # 2. 填充现有数据的 client_id（使用 DB 生成随机值）
    op.execute(
        "UPDATE alert_sources SET client_id = substr(md5(random()::text), 1, 8) WHERE client_id IS NULL"
    )
    # 3. 设置非空约束
    op.alter_column('alert_sources', 'client_id', nullable=False)


def downgrade() -> None:
    op.drop_column('alert_sources', 'client_id')
