"""Add namespace, instance_id, instance_name to alerts

Revision ID: 007_add_alert_cloud_fields
Revises: 006_cloud_product_metrics
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007_add_alert_cloud_fields'
down_revision: Union[str, None] = '006_cloud_product_metrics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alerts', sa.Column('namespace', sa.String(64), nullable=True))
    op.add_column('alerts', sa.Column('instance_id', sa.String(128), nullable=True))
    op.add_column('alerts', sa.Column('instance_name', sa.String(256), nullable=True))
    op.create_index('idx_alerts_namespace', 'alerts', ['namespace'])


def downgrade() -> None:
    op.drop_index('idx_alerts_namespace', 'alerts')
    op.drop_column('alerts', 'namespace')
    op.drop_column('alerts', 'instance_id')
    op.drop_column('alerts', 'instance_name')
