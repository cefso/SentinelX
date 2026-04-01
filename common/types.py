"""
SentinelX - 公共类型定义
后端和 Agent 共享的 Pydantic 类型注解
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============ 告警相关类型 ============
AlertLabels = dict[str, str]
"""告警标签，键值对形式，如 {"cluster": "prod-k8s", "env": "production"}"""


AlertAnnotations = dict[str, str]
"""告警注解，包含告警的额外描述信息"""


AlertMetrics = dict[str, Any]
"""告警指标数据"""


class AlertLabelsPayload(BaseModel):
    """告警标签负载（Agent 端使用）"""
    cluster: Optional[str] = Field(default=None, description="集群名称")
    env: Optional[str] = Field(default=None, description="环境")
    region: Optional[str] = Field(default=None, description="地域")
    service: Optional[str] = Field(default=None, description="服务名")
    instance: Optional[str] = Field(default=None, description="实例")
    job: Optional[str] = Field(default=None, description="Job 名称")
    # 允许额外的自定义标签
    extra: dict[str, str] = Field(default_factory=dict)


# ============ 健康状态类型 ============
class HealthStatus(BaseModel):
    """健康检查状态"""
    status: str = Field(..., description="状态: healthy/unhealthy")
    agent_id: str = Field(..., description="Agent ID")
    hostname: str = Field(..., description="主机名")
    timestamp: str = Field(..., description="检查时间 ISO 格式")
    version: Optional[str] = Field(default=None, description="Agent 版本")


# ============ 心跳类型 ============
class HeartbeatPayload(BaseModel):
    """心跳负载"""
    agent_id: str = Field(..., description="Agent ID")
    timestamp: str = Field(..., description="心跳时间 ISO 格式")
    status: str = Field(default="online", description="在线状态")
    cpu_percent: float = Field(default=0.0, ge=0, le=100, description="CPU 使用率")
    memory_percent: float = Field(default=0.0, ge=0, le=100, description="内存使用率")


# ============ 指标类型 ============
class MetricsPayload(BaseModel):
    """指标收集负载"""
    agent_id: str = Field(..., description="Agent ID")
    timestamp: str = Field(..., description="收集时间 ISO 格式")
    metrics: list[dict[str, Any]] = Field(default_factory=list, description="指标列表")


class MetricPoint(BaseModel):
    """单个指标点"""
    name: str = Field(..., description="指标名称，如 system.cpu.usage")
    value: float = Field(..., description="指标值")
    timestamp: str = Field(..., description="采集时间 ISO 格式")
    labels: AlertLabels = Field(default_factory=dict, description="指标标签")


# ============ 命令执行类型 ============
class CommandRequest(BaseModel):
    """平台下发的命令请求"""
    id: str = Field(..., description="命令 ID")
    type: str = Field(..., description="命令类型: shell/health_check/collect_logs")
    params: dict[str, Any] = Field(default_factory=dict, description="命令参数")
    timeout: int = Field(default=60, ge=1, le=3600, description="超时时间（秒）")


class CommandResult(BaseModel):
    """命令执行结果"""
    id: str = Field(..., description="命令 ID")
    status: str = Field(..., description="执行状态: success/error")
    output: str = Field(default="", description="命令输出")
    error: Optional[str] = Field(default=None, description="错误信息")
    duration_ms: Optional[int] = Field(default=None, description="执行耗时（毫秒）")


# ============ Agent 注册类型 ============
class AgentRegistration(BaseModel):
    """Agent 注册信息"""
    agent_id: str = Field(..., description="Agent ID")
    hostname: str = Field(..., description="主机名")
    ip_address: str = Field(..., description="IP 地址")
    tags: dict[str, str] = Field(default_factory=dict, description="标签")
    version: str = Field(default="1.0.0", description="Agent 版本")
    os: Optional[str] = Field(default=None, description="操作系统")
    python_version: Optional[str] = Field(default=None, description="Python 版本")


# ============ 追踪类型 ============
class TraceStep(BaseModel):
    """追踪步骤"""
    type: str = Field(..., description="步骤类型: received/dedup_check/rule_match/notification")
    time: str = Field(..., description="时间 ISO 格式")
    status: str = Field(..., description="状态: success/failed/skipped")
    duration_ms: Optional[int] = Field(default=None, description="耗时")
    detail: Optional[str] = Field(default=None, description="详细信息")
