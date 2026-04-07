"""add deduplication_config to alert_rules

Revision ID: 009_add_deduplication_config
Revises: 008_add_aliyun_cms_namespace
Create Date: 2026-04-07 09:17:50.644281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009_add_deduplication_config'
down_revision: Union[str, None] = '008_add_aliyun_cms_namespace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alert_rules', sa.Column('deduplication_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('alert_rules', 'deduplication_config')
