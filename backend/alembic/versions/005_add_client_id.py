"""Add client_id to alert_sources

Revision ID: 005_add_client_id
Revises: 004_add_user_approval
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005_add_client_id'
down_revision: Union[str, None] = '004_add_user_approval'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Column already exists in database from previous migration
    # This is a stub migration to maintain alembic revision chain
    pass


def downgrade() -> None:
    pass
