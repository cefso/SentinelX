"""
SentinelX - 告警数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index, ForeignKey
from apps.core.database import Base


class AlertSource(Base):
    """告警源配置"""

    __tablename__ = "alert_sources"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)

    name = Column(String(128), nullable=False)
    code = Column(String(64), nullable=False, unique=True)  # 如: prometheus-01
    source_type = Column(String(32), nullable=False)  # prometheus/zabbix/aliyun/tencent/custom

    # 配置 (JSONB) - 存储适配器配置、认证信息等
    config = Column(JSON, default=dict)

    # 加密的密钥
    secret_key = Column(String(512), nullable=True)  # AES加密存储

    # 状态
    is_active = Column(String(8), default="active")  # active/inactive
    description = Column(Text, nullable=True)

    # 客户端生成的唯一ID（用于 webhook URL）
    client_id = Column(String(32), unique=True, nullable=False, index=True)

    # 统计
    alert_count = Column(Integer, default=0)  # 累计接收告警数
    last_alert_at = Column(DateTime, nullable=True)  # 最后接收时间

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alert(Base):
    """告警实例"""

    __tablename__ = "alerts"
    __table_args__ = (
        # 普通索引
        Index("idx_alerts_labels", "tenant_id", "labels"),
        Index("idx_alerts_fired_at", "tenant_id", "fired_at"),
        Index("idx_alerts_status_severity", "tenant_id", "status", "severity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)

    # 核心字段
    alert_key = Column(String(256), nullable=False, index=True)  # 告警唯一标识
    fingerprint = Column(String(64), nullable=False, index=True)  # 告警指纹(用于去重)
    source = Column(String(64), nullable=False, index=True)  # 告警来源
    source_id = Column(Integer, ForeignKey("alert_sources.id"), nullable=True)

    title = Column(String(512))
    content = Column(Text)

    # 严重级别
    severity = Column(String(32), nullable=False, index=True)  # critical/high/medium/low/info

    # 状态: firing(触发中)/resolved(已恢复)/suppressed(已抑制)
    status = Column(String(32), nullable=False, index=True, default="firing")

    # JSONB动态字段
    labels = Column(JSON, default=dict)  # 告警标签 {env: prod, cluster: k8s}
    annotations = Column(JSON, default=dict)  # 告警注解 {description: xxx, runbook: url}
    metric_name = Column(String(256))  # 指标名
    metric_value = Column(JSON)  # 指标值 (支持任意类型)
    raw_data = Column(JSON, default=dict)  # 原始告警数据(完整保留)
    extra_data = Column(JSON, default=dict)  # 扩展数据(供AI分析等)

    # 云产品字段
    namespace = Column(String(64), nullable=True, index=True)  # 云产品命名空间
    instance_id = Column(String(128), nullable=True)  # 实例ID
    instance_name = Column(String(256), nullable=True)  # 实例名称

    # 追踪
    trace_id = Column(String(12), nullable=True, index=True)

    # 告警计数
    fire_count = Column(Integer, default=1)  # 触发次数
    repeat_count = Column(Integer, default=0)  # 重复次数

    # 负责人
    assignee_id = Column(Integer, nullable=True, index=True)  # 处理人
    assignee_name = Column(String(64), nullable=True)

    # 时间
    fired_at = Column(DateTime, default=datetime.utcnow, index=True)  # 触发时间
    resolved_at = Column(DateTime, nullable=True)  # 恢复时间
    acknowledged_at = Column(DateTime, nullable=True)  # 确认时间
    silenced_until = Column(DateTime, nullable=True)  # 静默截止时间

    # 升级
    escalation_count = Column(Integer, default=0)  # 升级次数

    # 路由信息
    matched_rules = Column(JSON, default=list)  # 匹配的规则列表
    notification_channels = Column(JSON, default=list)  # 通知渠道列表

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertHistory(Base):
    """告警历史"""

    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    alert_id = Column(Integer, nullable=False, index=True)

    # 操作类型: state_change/assign/escalate/silence/annotate
    action = Column(String(32), nullable=False)
    description = Column(Text, nullable=True)

    # 操作人
    operator_id = Column(Integer, nullable=True)
    operator_name = Column(String(64), nullable=True)

    # 变更前后
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AlertTrace(Base):
    """告警追踪"""

    __tablename__ = "alert_traces"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(12), unique=True, index=True)  # 短Trace ID
    alert_id = Column(String(64), index=True)  # 关联告警ID
    tenant_id = Column(String(64), index=True)

    # 处理结果
    final_status = Column(String(32))  # sent/suppressed/duplicate/failed
    deduction_reason = Column(Text)  # 去重原因
    suppress_reason = Column(Text)  # 抑制原因
    aggregate_info = Column(JSON)  # 聚合信息
    matched_rules = Column(JSON)  # 匹配的规则列表
    notification_channels = Column(JSON)  # 通知渠道

    # 完整步骤链 (JSON数组)
    steps_chain = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    expired_at = Column(DateTime)  # 7天后过期


class CloudProductMetric(Base):
    """云产品指标映射"""

    __tablename__ = "cloud_product_metrics"

    id = Column(Integer, primary_key=True, index=True)
    product = Column(String(64), nullable=False, index=True)  # 产品名称，如 "阿里云ECS"
    namespace = Column(String(128), nullable=False, index=True)  # 命名空间，如 "acs_ecs_dashboard"
    metric_name = Column(String(128), nullable=False)  # 指标名，如 "CPUUtilization"
    metric_desc = Column(String(256))  # 指标描述
    unit = Column(String(32))  # 单位
    dimensions = Column(JSON, default=list)  # 维度列表
    is_active = Column(Integer, default=1)  # 启用状态
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
