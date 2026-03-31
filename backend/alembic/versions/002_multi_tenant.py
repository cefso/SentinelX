"""Multi-tenant support migration

Revision ID: 002_multi_tenant
Revises: 001_initial
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_multi_tenant'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 在 users 表添加 is_system 字段
    op.add_column('users', sa.Column('is_system', sa.Boolean(), nullable=True, default=False))

    # 2. 创建 user_tenants 表 (替代 user_roles)
    op.create_table(
        'user_tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant')
    )
    op.create_index('idx_user_tenant_user', 'user_tenants', ['user_id'], unique=False)
    op.create_index('idx_user_tenant_tenant', 'user_tenants', ['tenant_id'], unique=False)

    # 3. 创建 user_teams 表
    op.create_table(
        'user_teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_team_user', 'user_teams', ['user_id'], unique=False)
    op.create_index('idx_user_team_team', 'user_teams', ['team_id'], unique=False)

    # 4. 在 roles 表添加 scope 字段
    op.add_column('roles', sa.Column('scope', sa.String(length=32), nullable=True, default='tenant'))

    # 5. 删除 user_roles 表 (需要先删除外键)
    op.drop_index('ix_user_roles_user_id', table_name='user_roles')
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_index('ix_user_roles_id', table_name='user_roles')
    op.drop_table('user_roles')

    # 6. 删除 users.tenant_id 列 (保留 is_system)
    # 先删除索引
    op.drop_index('ix_users_tenant_id', table_name='users')
    # 删除列
    op.drop_column('users', 'tenant_id')


def downgrade() -> None:
    # 恢复操作
    # 1. 添加回 tenant_id
    op.add_column('users', sa.Column('tenant_id', sa.Integer(), nullable=True))

    # 2. 重建 user_roles 表
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'], unique=False)
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'], unique=False)

    # 3. 删除 user_teams 表
    op.drop_index('idx_user_team_team', table_name='user_teams')
    op.drop_index('idx_user_team_user', table_name='user_teams')
    op.drop_table('user_teams')

    # 4. 删除 user_tenants 表
    op.drop_index('idx_user_tenant_tenant', table_name='user_tenants')
    op.drop_index('idx_user_tenant_user', table_name='user_tenants')
    op.drop_table('user_tenants')

    # 5. 删除 is_system 列
    op.drop_column('users', 'is_system')

    # 6. 删除 scope 列
    op.drop_column('roles', 'scope')

    # 7. 重建索引
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'], unique=False)
