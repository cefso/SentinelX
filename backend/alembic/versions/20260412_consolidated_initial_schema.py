"""consolidated_initial_schema

Consolidated initial migration replacing 001_initial through 014_add_callback_token.
This migration creates the complete SentinelX schema from scratch.

Revision ID: consolidated_initial
Revises:
Create Date: 2026-04-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'consolidated_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Extensions ───────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ─── pgmq verification (SQL-only mode, installed via init-db.sh) ─
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

    # ─── Tables (dependency order) ────────────────────────────────────

    # tenants
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('api_token', sa.String(length=256), nullable=True),
        sa.Column('webhook_api_key', sa.String(length=256), nullable=True),
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
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tenants_id', 'tenants', ['id'], unique=False)
    op.create_index('ix_tenants_name', 'tenants', ['name'], unique=True)
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)

    # users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('is_system', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # roles
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=True),
        sa.Column('scope', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uq_role_tenant_code'),
    )
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)

    # teams
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('leader_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_teams_id', 'teams', ['id'], unique=False)

    # user_tenants
    op.create_table(
        'user_tenants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant'),
    )
    op.create_index('idx_user_tenant_user', 'user_tenants', ['user_id'], unique=False)
    op.create_index('idx_user_tenant_tenant', 'user_tenants', ['tenant_id'], unique=False)

    # user_teams
    op.create_table(
        'user_teams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_teams_id', 'user_teams', ['id'], unique=False)
    op.create_index('ix_user_teams_user_id', 'user_teams', ['user_id'], unique=False)
    op.create_index('ix_user_teams_team_id', 'user_teams', ['team_id'], unique=False)

    # alert_sources
    op.create_table(
        'alert_sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('secret_key', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.String(length=8), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('client_id', sa.String(length=32), nullable=False),
        sa.Column('alert_count', sa.Integer(), nullable=True),
        sa.Column('last_alert_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_sources_id', 'alert_sources', ['id'], unique=False)
    op.create_index('ix_alert_sources_tenant_id', 'alert_sources', ['tenant_id'], unique=False)
    op.create_index('ix_alert_sources_code', 'alert_sources', ['code'], unique=True)
    op.create_index('ix_alert_sources_client_id', 'alert_sources', ['client_id'], unique=True)

    # alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
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
        sa.Column('namespace', sa.String(length=64), nullable=True),
        sa.Column('instance_id', sa.String(length=128), nullable=True),
        sa.Column('instance_name', sa.String(length=256), nullable=True),
        sa.Column('trace_id', sa.String(length=12), nullable=True),
        sa.Column('fire_count', sa.Integer(), nullable=True),
        sa.Column('repeat_count', sa.Integer(), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('assignee_name', sa.String(length=64), nullable=True),
        sa.Column('fired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('silenced_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalation_count', sa.Integer(), nullable=True),
        sa.Column('matched_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('callback_token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['alert_sources.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'], unique=False)
    op.create_index('ix_alerts_tenant_id', 'alerts', ['tenant_id'], unique=False)
    op.create_index('ix_alerts_alert_key', 'alerts', ['alert_key'], unique=False)
    op.create_index('ix_alerts_fingerprint', 'alerts', ['fingerprint'], unique=False)
    op.create_index('ix_alerts_source', 'alerts', ['source'], unique=False)
    op.create_index('ix_alerts_severity', 'alerts', ['severity'], unique=False)
    op.create_index('ix_alerts_status', 'alerts', ['status'], unique=False)
    op.create_index('ix_alerts_namespace', 'alerts', ['namespace'], unique=False)
    op.create_index('ix_alerts_trace_id', 'alerts', ['trace_id'], unique=False)
    op.create_index('ix_alerts_fired_at', 'alerts', ['fired_at'], unique=False)
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'], unique=False)
    op.create_index('ix_alerts_callback_token', 'alerts', ['callback_token'], unique=False)
    # GIN index for JSONB label queries
    op.create_index('ix_alerts_labels_gin', 'alerts', ['labels'],
                    postgresql_using='gin', postgresql_ops={'labels': 'jsonb_path_ops'})
    # Composite indexes
    op.create_index('idx_alerts_labels', 'alerts', ['tenant_id', 'labels'], unique=False)
    op.create_index('idx_alerts_fired_at', 'alerts', ['tenant_id', 'fired_at'], unique=False)
    op.create_index('idx_alerts_status_severity', 'alerts', ['tenant_id', 'status', 'severity'], unique=False)

    # alert_history
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('operator_id', sa.Integer(), nullable=True),
        sa.Column('operator_name', sa.String(length=64), nullable=True),
        sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_history_id', 'alert_history', ['id'], unique=False)
    op.create_index('ix_alert_history_tenant_id', 'alert_history', ['tenant_id'], unique=False)
    op.create_index('ix_alert_history_alert_id', 'alert_history', ['alert_id'], unique=False)

    # alert_traces
    op.create_table(
        'alert_traces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=12), nullable=True),
        sa.Column('alert_id', sa.String(length=64), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('final_status', sa.String(length=32), nullable=True),
        sa.Column('deduction_reason', sa.Text(), nullable=True),
        sa.Column('suppress_reason', sa.Text(), nullable=True),
        sa.Column('aggregate_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('matched_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notification_channels', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('steps_chain', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expired_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_traces_id', 'alert_traces', ['id'], unique=False)
    op.create_index('ix_alert_traces_trace_id', 'alert_traces', ['trace_id'], unique=True)

    # alert_rules
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
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
        sa.Column('deduplication_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('match_count', sa.Integer(), nullable=True),
        sa.Column('last_match_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_rules_id', 'alert_rules', ['id'], unique=False)
    op.create_index('ix_alert_rules_tenant_id', 'alert_rules', ['tenant_id'], unique=False)
    op.create_index('idx_rules_tenant_priority', 'alert_rules', ['tenant_id', 'priority'], unique=False)

    # notification_channels
    op.create_table(
        'notification_channels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
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
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_channels_id', 'notification_channels', ['id'], unique=False)
    op.create_index('ix_notification_channels_tenant_id', 'notification_channels', ['tenant_id'], unique=False)

    # notification_templates
    op.create_table(
        'notification_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
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
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_templates_id', 'notification_templates', ['id'], unique=False)
    op.create_index('ix_notification_templates_tenant_id', 'notification_templates', ['tenant_id'], unique=False)

    # notification_records
    op.create_table(
        'notification_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
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
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_records_id', 'notification_records', ['id'], unique=False)
    op.create_index('ix_notification_records_tenant_id', 'notification_records', ['tenant_id'], unique=False)
    op.create_index('ix_notification_records_alert_id', 'notification_records', ['alert_id'], unique=False)

    # audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
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
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('idx_audit_tenant_time', 'audit_logs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('idx_audit_user_time', 'audit_logs', ['user_id', 'created_at'], unique=False)

    # api_keys
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('key_id', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('secret_signature', sa.String(length=128), nullable=False),
        sa.Column('encrypted_secret', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_id', 'api_keys', ['id'], unique=False)
    op.create_index('ix_api_keys_key_id', 'api_keys', ['key_id'], unique=True)
    op.create_index('ix_api_keys_tenant_id', 'api_keys', ['tenant_id'], unique=False)
    op.create_index('idx_api_keys_key_id', 'api_keys', ['key_id'], unique=True)
    op.create_index('idx_api_keys_tenant', 'api_keys', ['tenant_id'], unique=False)

    # cloud_product_metrics
    op.create_table(
        'cloud_product_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product', sa.String(length=64), nullable=False),
        sa.Column('namespace', sa.String(length=128), nullable=False),
        sa.Column('metric_name', sa.String(length=128), nullable=False),
        sa.Column('metric_desc', sa.String(length=256), nullable=True),
        sa.Column('namespace_desc', sa.String(length=128), nullable=True),
        sa.Column('metric_name_desc', sa.String(length=256), nullable=True),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('dimensions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cloud_product_metrics_id', 'cloud_product_metrics', ['id'], unique=False)
    op.create_index('ix_cloud_product_metrics_product', 'cloud_product_metrics', ['product'], unique=False)
    op.create_index('ix_cloud_product_metrics_namespace', 'cloud_product_metrics', ['namespace'], unique=False)

    # alert_aggregate_groups
    op.create_table(
        'alert_aggregate_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('group_key', sa.String(length=256), nullable=False),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('alert_rules.id'), nullable=True),
        sa.Column('alert_count', sa.Integer(), nullable=True),
        sa.Column('fired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_alert_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_aggregate_groups_id', 'alert_aggregate_groups', ['id'], unique=False)
    op.create_index('ix_alert_aggregate_groups_tenant_id', 'alert_aggregate_groups', ['tenant_id'], unique=False)
    op.create_index('ix_alert_aggregate_groups_group_key', 'alert_aggregate_groups', ['group_key'], unique=False)

    # alert_aggregate_members
    op.create_table(
        'alert_aggregate_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('alert_aggregate_groups.id'), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alert_aggregate_members_id', 'alert_aggregate_members', ['id'], unique=False)
    op.create_index('ix_alert_aggregate_members_alert_id', 'alert_aggregate_members', ['alert_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('alert_aggregate_members')
    op.drop_table('alert_aggregate_groups')
    op.drop_table('cloud_product_metrics')
    op.drop_table('api_keys')
    op.drop_table('audit_logs')
    op.drop_table('notification_records')
    op.drop_table('notification_templates')
    op.drop_table('notification_channels')
    op.drop_table('alert_rules')
    op.drop_table('alert_traces')
    op.drop_table('alert_history')
    op.drop_table('alerts')
    op.drop_table('alert_sources')
    op.drop_table('user_teams')
    op.drop_table('user_tenants')
    op.drop_table('teams')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('tenants')
