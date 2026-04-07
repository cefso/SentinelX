"""change datetime columns to TIMESTAMP WITH TIME ZONE

Revision ID: 010_datetime_with_timezone
Revises: 009_add_deduplication_config
Create Date: 2026-04-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_datetime_with_timezone'
down_revision: Union[str, None] = '009_add_deduplication_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # alerts table
    op.execute("ALTER TABLE alerts ALTER COLUMN fired_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN resolved_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN acknowledged_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN silenced_until TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")

    # alert_sources table
    op.execute("ALTER TABLE alert_sources ALTER COLUMN last_alert_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alert_sources ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alert_sources ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")

    # alert_history table
    op.execute("ALTER TABLE alert_history ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")

    # alert_traces table
    op.execute("ALTER TABLE alert_traces ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE alert_traces ALTER COLUMN expired_at TYPE TIMESTAMP WITH TIME ZONE")

    # cloud_product_metrics table
    op.execute("ALTER TABLE cloud_product_metrics ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE cloud_product_metrics ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")

    # alert_aggregate_groups table (if exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alert_aggregate_groups') THEN
                ALTER TABLE alert_aggregate_groups ALTER COLUMN fired_at TYPE TIMESTAMP WITH TIME ZONE;
                ALTER TABLE alert_aggregate_groups ALTER COLUMN last_alert_at TYPE TIMESTAMP WITH TIME ZONE;
                ALTER TABLE alert_aggregate_groups ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;
                ALTER TABLE alert_aggregate_groups ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)

    # alert_aggregate_members table (if exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alert_aggregate_members') THEN
                ALTER TABLE alert_aggregate_members ALTER COLUMN added_at TYPE TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # alerts table
    op.execute("ALTER TABLE alerts ALTER COLUMN fired_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN resolved_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN acknowledged_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN silenced_until TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alerts ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # alert_sources table
    op.execute("ALTER TABLE alert_sources ALTER COLUMN last_alert_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alert_sources ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alert_sources ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # alert_history table
    op.execute("ALTER TABLE alert_history ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # alert_traces table
    op.execute("ALTER TABLE alert_traces ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE alert_traces ALTER COLUMN expired_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # cloud_product_metrics table
    op.execute("ALTER TABLE cloud_product_metrics ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE cloud_product_metrics ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # alert_aggregate_groups table
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alert_aggregate_groups') THEN
                ALTER TABLE alert_aggregate_groups ALTER COLUMN fired_at TYPE TIMESTAMP WITHOUT TIME ZONE;
                ALTER TABLE alert_aggregate_groups ALTER COLUMN last_alert_at TYPE TIMESTAMP WITHOUT TIME ZONE;
                ALTER TABLE alert_aggregate_groups ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE;
                ALTER TABLE alert_aggregate_groups ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;
        END $$;
    """)

    # alert_aggregate_members table
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alert_aggregate_members') THEN
                ALTER TABLE alert_aggregate_members ALTER COLUMN added_at TYPE TIMESTAMP WITHOUT TIME ZONE;
            END IF;
        END $$;
    """)