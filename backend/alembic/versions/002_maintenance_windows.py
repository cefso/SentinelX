"""Add maintenance_windows table

Revision ID: 002_maintenance_windows
Revises: 002_multi_tenant
Create Date: 2024-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_maintenance_windows'
down_revision: Union[str, None] = '002_multi_tenant'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'maintenance_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('suppressed_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_maintenance_windows_id', 'maintenance_windows', ['id'], unique=False)
    op.create_index('ix_maintenance_windows_tenant_id', 'maintenance_windows', ['tenant_id'], unique=False)
    op.create_index('idx_maintenance_tenant', 'maintenance_windows', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_maintenance_tenant', table_name='maintenance_windows')
    op.drop_index('ix_maintenance_windows_tenant_id', table_name='maintenance_windows')
    op.drop_index('ix_maintenance_windows_id', table_name='maintenance_windows')
    op.drop_table('maintenance_windows')
