"""Add callback_token to alerts

Revision ID: 014_add_callback_token
Revises: 013_add_pgmq
Create Date: 2026-04-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '014_add_callback_token'
down_revision: Union[str, None] = '013_add_pgmq'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column as nullable first
    op.add_column('alerts', sa.Column('callback_token', sa.String(64), nullable=True))
    op.create_index('ix_alerts_callback_token', 'alerts', ['callback_token'])

    # Backfill existing rows with random tokens in a single batch update
    conn = op.get_bind()
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    conn.execute(
        sa.text(
            "UPDATE alerts SET callback_token = encode(gen_random_bytes(32), 'hex') "
            "WHERE callback_token IS NULL"
        )
    )

    # Now make it NOT NULL
    op.alter_column('alerts', 'callback_token', nullable=False)


def downgrade() -> None:
    op.drop_index('ix_alerts_callback_token', table_name='alerts')
    op.drop_column('alerts', 'callback_token')
