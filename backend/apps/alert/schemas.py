"""
SentinelX - 告警Schema
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ 告警源Schema ============

class AlertSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=64)
    source_type: str = Field(..., min_length=1, max_length=32)
    config: Dict[str, Any] = {}
    description: Optional[str] = None


class AlertSourceCreate(AlertSourceBase):
    client_id: str = Field(..., min_length=1, max_length=32)


class AlertSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    code: Optional[str] = Field(None, min_length=1, max_length=64)
    source_type: Optional[str] = Field(None, min_length=1, max_length=32)
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[str] = Field(None, pattern="^(active|inactive)$")


class AlertSourceResponse(AlertSourceBase):
    id: int
    tenant_id: int
    is_active: str
    alert_count: int
    last_alert_at: Optional[datetime] = None
    created_at: datetime
    client_id: str

    class Config:
        from_attributes = True


# ============ 告警Schema ============

class AlertBase(BaseModel):
    alert_key: str = Field(..., min_length=1, max_length=256, description="告警键，告警唯一标识")
    source: str = Field(..., min_length=1, max_length=64, description="告警来源")
    title: str = Field(..., min_length=1, max_length=512, description="告警标题")
    content: Optional[str] = Field(None, description="告警内容")
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$", description="严重级别: critical/high/medium/low/info")
    labels: Dict[str, Any] = Field(default_factory=dict, description="告警标签，K/V键值对")
    annotations: Dict[str, Any] = Field(default_factory=dict, description="告警注解")
    metric_name: Optional[str] = Field(None, description="指标名称")
    metric_value: Optional[Any] = Field(None, description="指标值")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="原始告警数据")
    namespace: Optional[str] = Field(None, description="命名空间 / 云产品")
    instance_id: Optional[str] = Field(None, description="实例ID")
    instance_name: Optional[str] = Field(None, description="实例名称")


class AlertCreate(AlertBase):
    """创建告警请求"""
    fingerprint: Optional[str] = None  # 可选，不提供则自动生成
    trace_id: Optional[str] = None
    source_id: Optional[int] = None


class AlertUpdate(BaseModel):
    """更新告警状态"""
    status: Optional[str] = Field(None, pattern="^(firing|resolved|suppressed|acknowledged)$", description="状态: firing(触发中)/resolved(已恢复)/suppressed(已抑制)/acknowledged(已确认)")
    severity: Optional[str] = Field(None, pattern="^(critical|high|medium|low|info)$", description="严重级别: critical/high/medium/low/info")
    assignee_id: Optional[int] = Field(None, description="处理人ID")
    assignee_name: Optional[str] = Field(None, description="处理人名称")
    silenced_until: Optional[datetime] = Field(None, description="静默截止时间")
    annotations: Optional[Dict[str, Any]] = Field(None, description="告警注解")


class AlertResponse(AlertBase):
    """告警响应"""
    id: int = Field(..., description="告警ID")
    tenant_id: str = Field(..., description="租户ID")
    source_id: Optional[int] = Field(None, description="告警源ID")
    status: str = Field(..., description="状态: firing(触发中)/resolved(已恢复)/suppressed(已抑制)/acknowledged(已确认)")
    fingerprint: str = Field(..., description="指纹")
    trace_id: Optional[str] = Field(None, description="追踪ID")
    fire_count: int = Field(..., description="触发次数")
    repeat_count: int = Field(..., description="重复次数")
    assignee_id: Optional[int] = Field(None, description="处理人ID")
    assignee_name: Optional[str] = Field(None, description="处理人名称")
    fired_at: datetime = Field(..., description="触发时间")
    resolved_at: Optional[datetime] = Field(None, description="恢复时间")
    acknowledged_at: Optional[datetime] = Field(None, description="确认时间")
    silenced_until: Optional[datetime] = Field(None, description="静默截止时间")
    escalation_count: int = Field(..., description="升级次数")
    matched_rules: List[Dict[str, Any]] = Field(default_factory=list, description="匹配的规则列表")
    notification_channels: List[Any] = Field(default_factory=list, description="通知渠道列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """告警列表响应"""
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int


class AlertAggregatedItem(BaseModel):
    """聚合告警项"""
    fingerprint: str
    count: int
    latest: AlertResponse

    class Config:
        from_attributes = True


class AlertAggregatedResponse(BaseModel):
    """聚合告警响应"""
    items: List[AlertAggregatedItem]
    total: int
    page: int
    page_size: int


class AlertFilter(BaseModel):
    """告警过滤条件"""
    status: Optional[str] = Field(None, description="状态过滤")
    severity: Optional[List[str]] = Field(None, description="严重级别列表")
    source: Optional[str] = Field(None, description="告警来源过滤")
    assignee_id: Optional[int] = Field(None, description="处理人ID过滤")
    labels: Optional[Dict[str, str]] = Field(None, description="标签过滤")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    keyword: Optional[str] = Field(None, description="搜索关键词(标题/内容)")


# ============ 告警统计Schema ============

class AlertStats(BaseModel):
    """告警统计"""
    total: int = Field(..., description="总告警数")
    firing: int = Field(..., description="触发中告警数")
    resolved: int = Field(..., description="已恢复告警数")
    suppressed: int = Field(..., description="已抑制告警数")
    critical: int = Field(..., description="Critical级别数")
    high: int = Field(..., description="High级别数")
    medium: int = Field(..., description="Medium级别数")
    low: int = Field(..., description="Low级别数")
    info: int = Field(..., description="Info级别数")
    unassigned: int = Field(..., description="未指派告警数")
    unique: int = Field(..., description="去重告警数(不同指纹)")
    today: int = Field(..., description="今日新增告警数")
    firing_critical: int = Field(..., description="触发中Critical告警数")
    firing_high: int = Field(..., description="触发中High告警数")


# ============ 告警历史Schema ============

class AlertHistoryResponse(BaseModel):
    """告警历史"""
    id: int = Field(..., description="历史记录ID")
    tenant_id: str = Field(..., description="租户ID")
    alert_id: int = Field(..., description="告警ID")
    action: str = Field(..., description="操作类型: state_change/assign/escalate/silence/annotate")
    description: Optional[str] = Field(None, description="操作描述")
    operator_id: Optional[int] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人名称")
    old_value: Optional[Dict] = Field(None, description="变更前的值")
    new_value: Optional[Dict] = Field(None, description="变更后的值")
    created_at: datetime = Field(..., description="操作时间")

    class Config:
        from_attributes = True


# ============ Trace诊断Schema ============

class TraceStep(BaseModel):
    """追踪步骤"""
    step: int = Field(..., description="步骤序号")
    type: str = Field(..., description="步骤类型: received/dedup_check/suppress_check/rule_match/notification_sent等")
    title: str = Field(..., description="步骤标题")
    description: str = Field(..., description="步骤描述")
    status: str = Field(..., description="状态: success/passed/failed/blocked")
    details: Optional[Dict] = Field(None, description="详细信息")
    reason: Optional[str] = Field(None, description="原因")
    time: Optional[str] = Field(None, description="执行时间")


class AlertAggregateMemberItem(BaseModel):
    """聚合告警组成员项"""
    alert_id: int = Field(..., description="告警ID")
    title: str = Field(..., description="告警标题")
    severity: str = Field(..., description="严重级别")
    fired_at: datetime = Field(..., description="触发时间")
    source: str = Field(..., description="告警来源")
    status: str = Field(..., description="状态")
    added_at: datetime = Field(..., description="加入时间")

    class Config:
        from_attributes = True


class AlertAggregateMembersResponse(BaseModel):
    """聚合告警组成员响应"""
    items: List[AlertAggregateMemberItem] = Field(default_factory=list, description="成员列表")
    total: int = Field(..., description="总数")
    group_key: Optional[str] = Field(None, description="聚合组Key")
    alert_count: int = Field(..., description="组内告警数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class DiagnosisResponse(BaseModel):
    """诊断结果"""
    trace_id: str = Field(..., description="追踪ID")
    summary: Dict[str, Any] = Field(default_factory=dict, description="处理摘要")
    matched_rules: List[Dict[str, Any]] = Field(default_factory=list, description="匹配的规则")
    flow_steps: List[TraceStep] = Field(default_factory=list, description="处理流程步骤")
    timeline: List[Dict[str, str]] = Field(default_factory=list, description="时间线")


# ============ 云产品指标Schema ============

class CloudProductMetricBase(BaseModel):
    product: str = Field(..., min_length=1, max_length=64, description="产品名称")
    namespace: str = Field(..., min_length=1, max_length=128, description="命名空间")
    metric_name: str = Field(..., min_length=1, max_length=128, description="指标名")
    metric_desc: Optional[str] = Field(None, max_length=256, description="指标描述")
    namespace_desc: Optional[str] = Field(None, max_length=128, description="命名空间中文名")
    metric_name_desc: Optional[str] = Field(None, max_length=256, description="指标名称中文名")
    unit: Optional[str] = Field(None, max_length=32, description="单位")
    dimensions: Optional[List[Any]] = Field(default_factory=list, description="维度列表")
    is_active: Optional[int] = Field(1, description="启用状态: 1=启用, 0=禁用")


class CloudProductMetricCreate(CloudProductMetricBase):
    """创建云产品指标"""
    pass


class CloudProductMetricUpdate(BaseModel):
    """更新云产品指标"""
    product: Optional[str] = Field(None, min_length=1, max_length=64)
    namespace: Optional[str] = Field(None, min_length=1, max_length=128)
    metric_name: Optional[str] = Field(None, min_length=1, max_length=128)
    metric_desc: Optional[str] = Field(None, max_length=256)
    namespace_desc: Optional[str] = Field(None, max_length=128)
    metric_name_desc: Optional[str] = Field(None, max_length=256)
    unit: Optional[str] = Field(None, max_length=32)
    dimensions: Optional[List[Any]] = None
    is_active: Optional[int] = None


class CloudProductMetricResponse(CloudProductMetricBase):
    """云产品指标响应"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CloudMetricsListResponse(BaseModel):
    """云产品指标列表响应（分页）"""
    items: List[CloudProductMetricResponse]
    total: int
    page: int
    page_size: int
