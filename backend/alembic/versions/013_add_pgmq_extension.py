"""Add pgmq extension

Revision ID: 013_add_pgmq
Revises: 012_add_aggregate_tables
Create Date: 2026-04-12

"""
from typing import Sequence, Union
from alembic import op

revision: str = '013_add_pgmq'
down_revision: Union[str, None] = '012_add_aggregate_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgmq CASCADE;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pgmq CASCADE;")
