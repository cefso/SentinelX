"""Add cloud_product_metrics table

Revision ID: 006_cloud_product_metrics
Revises: 005_add_client_id
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006_cloud_product_metrics'
down_revision: Union[str, None] = '005_add_client_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cloud_product_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('product', sa.String(length=64), nullable=False, index=True),
        sa.Column('namespace', sa.String(length=128), nullable=False, index=True),
        sa.Column('metric_name', sa.String(length=128), nullable=False),
        sa.Column('metric_desc', sa.String(length=256), nullable=True),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('dimensions', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_cloud_product_namespace', 'cloud_product_metrics', ['namespace'])
    op.create_index('idx_cloud_product_product', 'cloud_product_metrics', ['product'])

    # 插入初始数据
    op.execute("""
        INSERT INTO cloud_product_metrics (product, namespace, metric_name, metric_desc, unit, dimensions, is_active)
        VALUES
        -- 阿里云 ECS
        ('阿里云ECS', 'acs_ecs', 'CPUUtilization', 'CPU使用率', '%', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'MemoryUsage', '内存使用率', '%', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'DiskUsage', '磁盘使用率', '%', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'InternetInRate', '公网入带宽', 'bps', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'InternetOutRate', '公网出带宽', 'bps', '["instanceId"]', 1),
        -- 阿里云 RDS
        ('阿里云RDS', 'acs_rds_dashboard', 'CPUUsage', 'CPU使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds_dashboard', 'MemoryUsage', '内存使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds_dashboard', 'DiskUsage', '磁盘使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds_dashboard', 'ConnectionUsage', '连接数使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds_dashboard', 'QPS', '每秒查询数', 'count/s', '["instanceId"]', 1),
        -- 阿里云 SLB
        ('阿里云SLB', 'acs_slb_dashboard', 'TrafficRX', '入流量', 'bps', '["instanceId", "vip"]', 1),
        ('阿里云SLB', 'acs_slb_dashboard', 'TrafficTX', '出流量', 'bps', '["instanceId", "vip"]', 1),
        ('阿里云SLB', 'acs_slb_dashboard', 'ActiveConnection', '活跃连接数', 'count', '["instanceId", "vip"]', 1),
        -- 阿里云 Redis
        ('阿里云Redis', 'acs_kvstore', 'MemoryUsage', '内存使用率', '%', '["instanceId"]', 1),
        ('阿里云Redis', 'acs_kvstore', 'QPS', '每秒命令数', 'count/s', '["instanceId"]', 1),
        ('阿里云Redis', 'acs_kvstore', 'ConnectionUsage', '连接数使用率', '%', '["instanceId"]', 1),
        -- 腾讯云 CVM
        ('腾讯云CVM', 'QCE/CVM', 'CPUUsage', 'CPU使用率', '%', '["unInstanceId"]', 1),
        ('腾讯云CVM', 'QCE/CVM', 'MemUsage', '内存使用率', '%', '["unInstanceId"]', 1),
        ('腾讯云CVM', 'QCE/CVM', 'DiskUsage', '磁盘使用率', '%', '["unInstanceId"]', 1),
        ('腾讯云CVM', 'QCE/CVM', 'InternetInRate', '公网入带宽', 'bps', '["unInstanceId"]', 1),
        ('腾讯云CVM', 'QCE/CVM', 'InternetOutRate', '公网出带宽', 'bps', '["unInstanceId"]', 1),
        -- 腾讯云 CBS
        ('腾讯云CBS', 'QCE/CBS', 'DiskUsage', '磁盘使用率', '%', '["diskId"]', 1),
        ('腾讯云CBS', 'QCE/CBS', 'DiskIops', '磁盘IOPS', 'iops', '["diskId"]', 1),
        -- 腾讯云 CLB
        ('腾讯云CLB', 'QCE/LOADBALANCE', 'TrafficRX', '入流量', 'bps', '["vip"]', 1),
        ('腾讯云CLB', 'QCE/LOADBALANCE', 'TrafficTX', '出流量', 'bps', '["vip"]', 1),
        ('腾讯云CLB', 'QCE/LOADBALANCE', 'ActiveConnection', '活跃连接数', 'count', '["vip"]', 1)
    """)


def downgrade() -> None:
    op.drop_table('cloud_product_metrics')
