"""
SentinelX - 规则数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Index
from apps.core.database import Base


class AlertRule(Base):
    """告警规则"""

    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("idx_rules_tenant_priority", "tenant_id", "priority"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    code = Column(String(64), nullable=False)  # 规则唯一标识
    description = Column(Text, nullable=True)

    # 规则条件 (JSON)
    conditions = Column(JSON, default=list)  # 条件列表
    condition_mode = Column(String(8), default="and")  # and/or

    # 匹配动作
    actions = Column(JSON, default=list)  # 发送渠道等

    # 状态
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # 优先级，数字越大优先级越高

    # 抑制配置
    suppress_config = Column(JSON, nullable=True)  # 抑制配置

    # 聚合配置
    aggregate_config = Column(JSON, nullable=True)  # 聚合配置

    # 统计
    match_count = Column(Integer, default=0)  # 累计匹配次数
    last_match_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationChannel(Base):
    """通知渠道"""

    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    code = Column(String(64), nullable=False)
    channel_type = Column(String(32), nullable=False)  # dingtalk/feishu/wecom/email/webhook

    # 配置 (JSONB)
    config = Column(JSON, default=dict)  # webhook_url, secret等

    # 加密字段
    secret_key = Column(String(512), nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # 是否为默认渠道

    # 统计
    send_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    last_send_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationTemplate(Base):
    """通知模板"""

    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(128), nullable=False)
    code = Column(String(64), nullable=False)
    channel_type = Column(String(32), nullable=False)  # 适用渠道类型

    # 模板内容 (Jinja2)
    content = Column(Text, nullable=False)

    # 状态
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # 变量定义
    variables = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationRecord(Base):
    """通知记录"""

    __tablename__ = "notification_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    alert_id = Column(Integer, nullable=False, index=True)

    channel_id = Column(Integer, nullable=False)
    channel_type = Column(String(32), nullable=False)

    # 发送状态: pending/success/failed
    status = Column(String(16), default="pending")
    error_message = Column(Text, nullable=True)

    # 发送详情
    request_data = Column(JSON, nullable=True)  # 请求数据
    response_data = Column(JSON, nullable=True)  # 响应数据

    # 重试
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
