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
    pass


class AlertSourceUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class AlertSourceResponse(AlertSourceBase):
    id: int
    tenant_id: int
    is_active: str
    alert_count: int
    last_alert_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 告警Schema ============

class AlertBase(BaseModel):
    alert_key: str = Field(..., min_length=1, max_length=256)
    source: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=512)
    content: Optional[str] = None
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$")
    labels: Dict[str, Any] = {}
    annotations: Dict[str, Any] = {}
    metric_name: Optional[str] = None
    metric_value: Optional[Any] = None
    raw_data: Dict[str, Any] = {}


class AlertCreate(AlertBase):
    """创建告警请求"""
    fingerprint: Optional[str] = None  # 可选，不提供则自动生成
    trace_id: Optional[str] = None


class AlertUpdate(BaseModel):
    """更新告警状态"""
    status: Optional[str] = Field(None, pattern="^(firing|resolved|suppressed)$")
    severity: Optional[str] = Field(None, pattern="^(critical|high|medium|low|info)$")
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    silenced_until: Optional[datetime] = None
    annotations: Optional[Dict[str, Any]] = None


class AlertResponse(AlertBase):
    """告警响应"""
    id: int
    tenant_id: str
    source_id: Optional[int] = None
    status: str
    fingerprint: str
    trace_id: Optional[str] = None
    fire_count: int
    repeat_count: int
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    fired_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    silenced_until: Optional[datetime] = None
    escalation_count: int
    matched_rules: List[Dict[str, Any]] = []
    notification_channels: List[str] = []
    created_at: datetime
    updated_at: datetime

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
    status: Optional[str] = None
    severity: Optional[List[str]] = None
    source: Optional[str] = None
    assignee_id: Optional[int] = None
    labels: Optional[Dict[str, str]] = None  # 标签过滤
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    keyword: Optional[str] = None  # 搜索标题/内容


# ============ 告警统计Schema ============

class AlertStats(BaseModel):
    """告警统计"""
    total: int
    firing: int
    resolved: int
    suppressed: int
    critical: int
    high: int
    medium: int
    low: int
    info: int
    unassigned: int
    unique: int
    today: int
    firing_critical: int
    firing_high: int


# ============ 告警历史Schema ============

class AlertHistoryResponse(BaseModel):
    id: int
    tenant_id: str
    alert_id: int
    action: str
    description: Optional[str] = None
    operator_id: Optional[int] = None
    operator_name: Optional[str] = None
    old_value: Optional[Dict] = None
    new_value: Optional[Dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Trace诊断Schema ============

class TraceStep(BaseModel):
    """追踪步骤"""
    step: int
    type: str  # received/dedup_check/suppress_check/rule_match/notification_sent等
    title: str
    description: str
    status: str  # success/passed/failed/blocked
    details: Optional[Dict] = None
    reason: Optional[str] = None
    time: Optional[str] = None


class DiagnosisResponse(BaseModel):
    """诊断结果"""
    trace_id: str
    summary: Dict[str, Any]
    matched_rules: List[Dict[str, Any]] = []
    flow_steps: List[TraceStep] = []
    timeline: List[Dict[str, str]] = []
