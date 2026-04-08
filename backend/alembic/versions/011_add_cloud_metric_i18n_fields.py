"""add namespace_desc and metric_name_desc to cloud_product_metrics

Revision ID: 011_add_cloud_metric_i18n_fields
Revises: 010_datetime_with_timezone
Create Date: 2026-04-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_add_cloud_metric_i18n_fields'
down_revision: Union[str, None] = '010_datetime_with_timezone'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cloud_product_metrics', sa.Column('namespace_desc', sa.String(128), nullable=True))
    op.add_column('cloud_product_metrics', sa.Column('metric_name_desc', sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column('cloud_product_metrics', 'metric_name_desc')
    op.drop_column('cloud_product_metrics', 'namespace_desc')
