"""unify tenant_id to Integer across business tables

Plan B: every tenant_id column matches tenants.id (Integer).
get_current_tenant_id returns int; business code no longer str()-casts.

Only alters columns that are still VARCHAR/text. Skips missing tables
and columns that are already INTEGER (e.g. newly created
maintenance_windows, pre-integer alert_sources).

Revision ID: 20260916_tenant_id_int
Revises: 20260819_optimize_history
Create Date: 2026-09-16
"""
from alembic import op
import sqlalchemy as sa

revision = "20260916_tenant_id_int"
down_revision = "20260819_optimize_history"
branch_labels = None
depends_on = None

TABLES = [
    "alerts",
    "alert_history",
    "alert_traces",
    "alert_aggregate_groups",
    "webhook_logs",
    "alert_rules",
    "notification_channels",
    "notification_templates",
    "notification_records",
    "audit_logs",
    "maintenance_windows",
]


def _table_exists(conn, table: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = current_schema() AND table_name = :t"
        ),
        {"t": table},
    ).first() is not None


def _column_data_type(conn, table: str, column: str) -> str | None:
    row = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first()
    return row[0] if row else None


def _alter_tenant_id_to_integer(conn, table: str) -> None:
    """Convert tenant_id to INTEGER only when it is still a string type."""
    data_type = _column_data_type(conn, table, "tenant_id")
    if data_type is None:
        return
    if data_type not in ("character varying", "character", "text"):
        return

    # Clean blank values first so the cast never sees ''
    op.execute(
        f"UPDATE {table} SET tenant_id = NULL "
        f"WHERE tenant_id IS NOT NULL AND btrim(tenant_id) = ''"
    )
    op.execute(
        f"ALTER TABLE {table} "
        f"ALTER COLUMN tenant_id TYPE INTEGER "
        f"USING CASE "
        f"WHEN btrim(tenant_id) = '' THEN NULL "
        f"ELSE btrim(tenant_id)::INTEGER "
        f"END"
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Model existed without a migration; create if missing (tenant_id already Integer)
    if not _table_exists(conn, "maintenance_windows"):
        op.create_table(
            "maintenance_windows",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.String(length=512), nullable=True),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("scope", sa.JSON(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("suppressed_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_maintenance_windows_id", "maintenance_windows", ["id"], unique=False
        )
        op.create_index(
            "ix_maintenance_windows_tenant_id",
            "maintenance_windows",
            ["tenant_id"],
            unique=False,
        )

    for table in TABLES:
        if not _table_exists(conn, table):
            continue
        _alter_tenant_id_to_integer(conn, table)


def downgrade() -> None:
    conn = op.get_bind()
    for table in TABLES:
        if not _table_exists(conn, table):
            continue
        data_type = _column_data_type(conn, table, "tenant_id")
        if data_type not in ("integer", "bigint", "smallint"):
            continue
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN tenant_id TYPE VARCHAR(64) "
            f"USING tenant_id::VARCHAR"
        )
