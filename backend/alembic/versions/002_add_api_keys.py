"""Add API Key index table for fast lookup

Revision ID: 002_add_api_keys
Revises: 001_initial
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_add_api_keys'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('key_id', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('secret_signature', sa.String(length=128), nullable=False),
        sa.Column('encrypted_secret', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_keys_key_id', 'api_keys', ['key_id'], unique=True)
    op.create_index('idx_api_keys_tenant', 'api_keys', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_api_keys_tenant', 'api_keys')
    op.drop_index('idx_api_keys_key_id', 'api_keys')
    op.drop_table('api_keys')
