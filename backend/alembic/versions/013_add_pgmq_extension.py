"""Add pgmq extension (SQL-only mode)

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
    # SQL-only 模式：pgmq 通过 init-db.sh 中 psql -f /tmp/pgmq.sql 安装
    # 不使用 CREATE EXTENSION，而是验证函数是否存在
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname = 'pgmq' AND p.proname = 'send'
            ) THEN
                RAISE EXCEPTION 'pgmq functions not installed. Run: psql -f /tmp/pgmq.sql';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # SQL-only 模式下只清理数据，不删除 schema（避免误删）
    op.execute("""
        DELETE FROM pgmq.meta WHERE true;
    """)
