"""Initial migration

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建租户表
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('api_token', sa.String(length=256), nullable=True),
        sa.Column('max_alerts', sa.Integer(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('max_rules', sa.Integer(), nullable=True),
        sa.Column('max_channels', sa.Integer(), nullable=True),
        sa.Column('alert_qps', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenants_id', 'tenants', ['id'], unique=False)
    op.create_index('ix_tenants_name', 'tenants', ['name'], unique=True)
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)

    # 创建用户表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 创建角色表
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)

    # 创建用户角色关联表
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

    # 创建团队表
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('leader_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_teams_id', 'teams', ['id'], unique=False)

    # 创建告警源表
    op.create_table(
        'alert_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('secret_key', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.String(length=8), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('alert_count', sa.Integer(), nullable=True),
        sa.Column('last_alert_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_sources_id', 'alert_sources', ['id'], unique=False)
    op.create_index('ix_alert_sources_tenant_id', 'alert_sources', ['tenant_id'], unique=False)
    op.create_index('ix_alert_sources_code', 'alert_sources', ['code'], unique=True)

    # 创建告警表
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('alert_key', sa.String(length=256), nullable=False),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('annotations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metric_name', sa.String(length=256), nullable=True),
        sa.Column('metric_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('trace_id', sa.String(length=12), nullable=True),
        sa.Column('fire_count', sa.Integer(), nullable=True),
        sa.Column('repeat_count', sa.Integer(), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('assignee_name', sa.String(length=64), nullable=True),
        sa.Column('fired_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('silenced_until', sa.DateTime(), nullable=True),
        sa.Column('escalation_count', sa.Integer(), nullable=True),
        sa.Column('matched_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['alert_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'], unique=False)
    op.create_index('ix_alerts_tenant_id', 'alerts', ['tenant_id'], unique=False)
    op.create_index('ix_alerts_alert_key', 'alerts', ['alert_key'], unique=False)
    op.create_index('ix_alerts_fingerprint', 'alerts', ['fingerprint'], unique=False)
    op.create_index('ix_alerts_source', 'alerts', ['source'], unique=False)
    op.create_index('ix_alerts_severity', 'alerts', ['severity'], unique=False)
    op.create_index('ix_alerts_status', 'alerts', ['status'], unique=False)
    op.create_index('ix_alerts_trace_id', 'alerts', ['trace_id'], unique=False)
    op.create_index('ix_alerts_fired_at', 'alerts', ['fired_at'], unique=False)
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'], unique=False)
    # GIN索引用于JSONB查询
    op.create_index('ix_alerts_labels', 'alerts', ['labels'], postgresql_using='gin', postgresql_ops={'labels': 'jsonb_path_ops'})
    op.create_index('idx_alerts_fired_at', 'alerts', ['tenant_id', 'fired_at'], unique=False)
    op.create_index('idx_alerts_status_severity', 'alerts', ['tenant_id', 'status', 'severity'], unique=False)

    # 创建告警历史表
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('operator_id', sa.Integer(), nullable=True),
        sa.Column('operator_name', sa.String(length=64), nullable=True),
        sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_history_id', 'alert_history', ['id'], unique=False)
    op.create_index('ix_alert_history_tenant_id', 'alert_history', ['tenant_id'], unique=False)
    op.create_index('ix_alert_history_alert_id', 'alert_history', ['alert_id'], unique=False)

    # 创建告警追踪表
    op.create_table(
        'alert_traces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trace_id', sa.String(length=12), nullable=False),
        sa.Column('alert_id', sa.String(length=64), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('final_status', sa.String(length=32), nullable=True),
        sa.Column('deduction_reason', sa.Text(), nullable=True),
        sa.Column('suppress_reason', sa.Text(), nullable=True),
        sa.Column('aggregate_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('matched_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('steps_chain', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expired_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_traces_id', 'alert_traces', ['id'], unique=False)
    op.create_index('ix_alert_traces_trace_id', 'alert_traces', ['trace_id'], unique=True)

    # 创建规则表
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('condition_mode', sa.String(length=8), nullable=True),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('suppress_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('aggregate_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('match_count', sa.Integer(), nullable=True),
        sa.Column('last_match_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alert_rules_id', 'alert_rules', ['id'], unique=False)
    op.create_index('ix_alert_rules_tenant_id', 'alert_rules', ['tenant_id'], unique=False)
    op.create_index('idx_rules_tenant_priority', 'alert_rules', ['tenant_id', 'priority'], unique=False)

    # 创建通知渠道表
    op.create_table(
        'notification_channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('channel_type', sa.String(length=32), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('secret_key', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('send_count', sa.Integer(), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=True),
        sa.Column('fail_count', sa.Integer(), nullable=True),
        sa.Column('last_send_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notification_channels_id', 'notification_channels', ['id'], unique=False)
    op.create_index('ix_notification_channels_tenant_id', 'notification_channels', ['tenant_id'], unique=False)

    # 创建通知模板表
    op.create_table(
        'notification_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('channel_type', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notification_templates_id', 'notification_templates', ['id'], unique=False)
    op.create_index('ix_notification_templates_tenant_id', 'notification_templates', ['tenant_id'], unique=False)

    # 创建通知记录表
    op.create_table(
        'notification_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('channel_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notification_records_id', 'notification_records', ['id'], unique=False)
    op.create_index('ix_notification_records_tenant_id', 'notification_records', ['tenant_id'], unique=False)
    op.create_index('ix_notification_records_alert_id', 'notification_records', ['alert_id'], unique=False)

    # 创建审计日志表
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', sa.String(length=128), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('idx_audit_tenant_time', 'audit_logs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('idx_audit_user_time', 'audit_logs', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    # 删除表顺序（反向）
    op.drop_table('audit_logs')
    op.drop_table('notification_records')
    op.drop_table('notification_templates')
    op.drop_table('notification_channels')
    op.drop_table('alert_rules')
    op.drop_table('alert_traces')
    op.drop_table('alert_history')
    op.drop_table('alerts')
    op.drop_table('alert_sources')
    op.drop_table('teams')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('tenants')
