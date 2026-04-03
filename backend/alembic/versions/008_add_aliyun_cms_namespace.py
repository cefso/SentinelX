"""Add aliyun_cms namespace mappings (acs_ecs, acs_rds, etc)

Revision ID: 008_add_aliyun_cms_namespace
Revises: 007_add_alert_cloud_fields
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '008_add_aliyun_cms_namespace'
down_revision: Union[str, None] = '007_add_alert_cloud_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加阿里云CMS 1.0使用的namespace映射

    真实数据中namespace格式如: acs_ecs, acs_rds 等
    先删除旧的 acs_ecs_dashboard 等命名空间数据，再插入正确的
    """
    # 先删除旧数据（如果有残留）
    op.execute("""
        DELETE FROM cloud_product_metrics
        WHERE namespace IN ('acs_ecs_dashboard', 'acs_rds_dashboard', 'acs_slb_dashboard', 'acs_kvstore')
    """)
    # 插入新数据
    op.execute("""
        INSERT INTO cloud_product_metrics (product, namespace, metric_name, metric_desc, unit, dimensions, is_active)
        VALUES
        -- 阿里云 ECS (acs_ecs - 真实数据格式)
        ('阿里云ECS', 'acs_ecs', 'CPUUtilization', 'CPU使用率', '%', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'MemoryUsage', '内存使用率', '%', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'DiskUsage', '磁盘使用率', '%', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'InternetInRate', '公网入带宽', 'bps', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'InternetOutRate', '公网出带宽', 'bps', '["instanceId"]', 1),
        ('阿里云ECS', 'acs_ecs', 'diskusage_utilization', '磁盘使用率', '%', '["instanceId"]', 1),
        -- 阿里云 RDS (acs_rds - 真实数据格式)
        ('阿里云RDS', 'acs_rds', 'CPUUsage', 'CPU使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds', 'MemoryUsage', '内存使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds', 'DiskUsage', '磁盘使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds', 'ConnectionUsage', '连接数使用率', '%', '["instanceId"]', 1),
        ('阿里云RDS', 'acs_rds', 'QPS', '每秒查询数', 'count/s', '["instanceId"]', 1),
        -- 阿里云 SLB (acs_slb - 真实数据格式)
        ('阿里云SLB', 'acs_slb', 'TrafficRX', '入流量', 'bps', '["instanceId", "vip"]', 1),
        ('阿里云SLB', 'acs_slb', 'TrafficTX', '出流量', 'bps', '["instanceId", "vip"]', 1),
        ('阿里云SLB', 'acs_slb', 'ActiveConnection', '活跃连接数', 'count', '["instanceId", "vip"]', 1),
        -- 阿里云 Redis (acs_kvstore - 真实数据格式)
        ('阿里云Redis', 'acs_kvstore', 'MemoryUsage', '内存使用率', '%', '["instanceId"]', 1),
        ('阿里云Redis', 'acs_kvstore', 'QPS', '每秒命令数', 'count/s', '["instanceId"]', 1),
        ('阿里云Redis', 'acs_kvstore', 'ConnectionUsage', '连接数使用率', '%', '["instanceId"]', 1)
    """)


def downgrade() -> None:
    """删除阿里云CMS 1.0 namespace映射"""
    op.execute("""
        DELETE FROM cloud_product_metrics
        WHERE namespace IN ('acs_ecs', 'acs_rds', 'acs_slb', 'acs_kvstore')
    """)
