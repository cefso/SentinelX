"""
SentinelX - 维护窗口数据模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Index
from apps.core.database import Base


class MaintenanceWindow(Base):
    """维护窗口"""

    __tablename__ = "maintenance_windows"
    __table_args__ = (
        Index("idx_maintenance_tenant", "tenant_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    description = Column(String(512), nullable=True)

    # 时间范围
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    # 影响的范围 (JSON) - 可按 labels/severity/source 过滤
    # 例如: {"labels": {"cluster": "prod"}, "severity": ["high", "critical"]}
    scope = Column(JSON, default=dict)

    # 状态
    is_active = Column(Boolean, default=True)

    # 统计
    suppressed_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
