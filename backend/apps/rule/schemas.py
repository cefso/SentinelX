"""
SentinelX - 规则Schema
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

from apps.alert.schemas import AlertResponse


# ============ 规则条件Schema ============

class Condition(BaseModel):
    """规则条件

    支持的字段路径:
    - 基础字段: alert_key, title, content, severity, status, source
    - 云产品字段: namespace, instance_id, instance_name
    - 指标字段: metric_name, metric_value
    - 标签/注解/原始数据: labels.xxx, annotations.xxx, raw_data.xxx
    - 统计字段: fire_count, repeat_count, escalation_count
    - 时间字段: fired_at (ISO格式字符串)
    - 追踪字段: trace_id

    支持的操作符:
    - 字符串: eq(等于), ne(不等于), contains(包含), not_contains(不包含), regex(正则), in(在列表中), not_in(不在列表中)
    - 数值: gt(大于), gte(大于等于), lt(小于), lte(小于等于)
    - 通用: exists(存在), is_empty(为空)
    """
    field: str = Field(..., description="字段路径，如 severity/labels.cluster")
    operator: str = Field(..., description="操作符: eq/ne/gt/gte/lt/lte/contains/not_contains/regex/in/not_in/exists/is_empty")
    value: Any = Field(..., description="比较值")
    key: Optional[str] = Field(None, description="标签字段的 key（用于 labels 字段的初始化）")


class RuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    conditions: List[Condition] = []
    condition_mode: str = Field("and", pattern="^(and|or)$")
    actions: List[str] = []  # 动作，如通知渠道ID列表
    priority: int = Field(0, ge=0, le=1000)
    suppress_config: Optional[Dict[str, Any]] = None
    aggregate_config: Optional[Dict[str, Any]] = None
    deduplication_config: Optional["DeduplicationConfig"] = None


# ============ 去重/抑制/聚合Config Schema ============


class DimensionsConfig(BaseModel):
    """维度配置"""
    by_severity: bool = False
    by_source: bool = False


class MaintenanceWindowConfig(BaseModel):
    """维护窗口配置"""
    cluster_labels: List[str] = []
    duration_minutes: int = 60


class RuleBasedSuppressionCondition(BaseModel):
    """基于规则的抑制条件"""
    field: str
    operator: str
    value: Any = None


class RuleBasedSuppressionConfig(BaseModel):
    """基于规则的抑制配置"""
    conditions: List[RuleBasedSuppressionCondition] = []
    delay_seconds: int = 0


class SuppressionConfig(BaseModel):
    """抑制配置"""
    enabled: bool = False
    type: Literal["maintenance_window", "rule_based"] = "maintenance_window"
    maintenance_window: Optional[MaintenanceWindowConfig] = None
    rule_based: Optional[RuleBasedSuppressionConfig] = None


class ConditionItem(BaseModel):
    """去重条件项"""
    field: str = Field(..., description="字段路径，如 labels.severity/severity/source")
    operator: str = Field(..., description="操作符: eq/ne/contains/in")
    value: Any = Field(..., description="比较值")
    key: Optional[str] = Field(None, description="标签字段的 key（用于 labels 字段的初始化）")


class FingerprintDeduplicationConfig(BaseModel):
    """指纹模式去重配置"""
    enabled: bool = False
    dedup_type: Literal["fingerprint"] = "fingerprint"
    fingerprint_fields: List[str] = Field(default_factory=lambda: ["alert_key"], description="指纹字段列表")
    window_seconds: int = Field(default=300, ge=0, description="去重窗口秒数")
    dimensions: DimensionsConfig = Field(default_factory=DimensionsConfig)
    strategy: Literal["first", "last"] = "first"


class ConditionDeduplicationConfig(BaseModel):
    """条件模式去重配置"""
    enabled: bool = False
    dedup_type: Literal["condition"] = "condition"
    conditions: List[ConditionItem] = Field(default_factory=list, description="去重条件列表")
    condition_mode: Literal["and", "or"] = "and"
    window_seconds: int = Field(default=300, ge=0, description="去重窗口秒数")
    strategy: Literal["first", "last"] = "first"


DeduplicationConfig = FingerprintDeduplicationConfig | ConditionDeduplicationConfig


class AggregationConfig(BaseModel):
    """聚合配置"""
    enabled: bool = False
    group_by: List[str] = []
    window_seconds: int = 300
    max_count: int = 100
    store_original_alerts: bool = False


class RuleCreate(RuleBase):
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[Condition]] = None
    condition_mode: Optional[str] = None
    actions: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    suppress_config: Optional[Dict[str, Any]] = None
    aggregate_config: Optional[Dict[str, Any]] = None
    deduplication_config: Optional["DeduplicationConfig"] = None


class RuleResponse(RuleBase):
    id: int
    tenant_id: str
    is_active: bool
    match_count: int
    last_match_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleTestRequest(BaseModel):
    """规则测试请求"""
    conditions: List[Condition]
    condition_mode: str = "and"
    test_data: Dict[str, Any] = {}


class RuleTestResponse(BaseModel):
    """规则测试响应"""
    matched: bool
    reason: Optional[str] = None
    evaluated_conditions: List[Dict[str, Any]] = []


# ============ 通知渠道Schema ============

class ChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=64)
    channel_type: str = Field(..., min_length=1, max_length=32)
    config: Dict[str, Any] = {}
    is_active: bool = True
    is_default: bool = False


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ChannelResponse(ChannelBase):
    id: int
    tenant_id: str
    send_count: int
    success_count: int
    fail_count: int
    last_send_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 通知模板Schema ============

class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=64)
    channel_type: str = Field(..., min_length=1, max_length=32)
    content: str = Field(..., min_length=1)
    variables: List[str] = []
    is_active: bool = True
    is_default: bool = False


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class TemplateResponse(TemplateBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 字段值查询Schema ============

class FieldValueItem(BaseModel):
    """字段值项"""
    value: str = Field(..., description="字段值")
    count: int = Field(..., description="出现次数")


class FieldValuesResponse(BaseModel):
    """字段值查询响应"""
    field: str = Field(..., description="字段路径")
    values: List[FieldValueItem] = Field(default_factory=list, description="可选值列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="本次返回数量")
    offset: int = Field(..., description="分页偏移")


# ============ 预览API Schema ============

class PreviewDedupRequest(BaseModel):
    """去重预览请求"""
    deduplication_config: DeduplicationConfig
    status: Optional[str] = Field(None, description="状态过滤: firing/resolved/suppressed")
    severity: Optional[str] = Field(None, description="严重级别过滤")
    source: Optional[str] = Field(None, description="告警来源过滤")


class PreviewAggregateRequest(BaseModel):
    """聚合预览请求"""
    aggregate_config: AggregationConfig
    status: Optional[str] = Field(None, description="状态过滤: firing/resolved/suppressed")
    severity: Optional[str] = Field(None, description="严重级别过滤")
    source: Optional[str] = Field(None, description="告警来源过滤")


class AlertGroupItem(BaseModel):
    """聚合组预览项"""
    group_key: str = Field(..., description="聚合组Key")
    group_count: int = Field(..., description="组内告警数量")
    latest: AlertResponse = Field(..., description="组内最新告警")

    class Config:
        from_attributes = True


class PreviewDedupResponse(BaseModel):
    """去重预览响应"""
    items: List[AlertResponse] = Field(default_factory=list, description="匹配的告警列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class PreviewAggregateResponse(BaseModel):
    """聚合预览响应"""
    items: List[AlertGroupItem] = Field(default_factory=list, description="聚合组列表")
    total: int = Field(..., description="总组数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


# ============ 策略配置API Schema ============

class StrategyDedupRequest(BaseModel):
    """去重策略更新请求"""
    config: Optional[Dict[str, Any]] = Field(None, description="去重配置，null 表示禁用")


class StrategySuppressRequest(BaseModel):
    """抑制策略更新请求"""
    config: Optional[Dict[str, Any]] = Field(None, description="抑制配置，null 表示禁用")


class StrategyAggregateRequest(BaseModel):
    """聚合策略更新请求"""
    config: Optional[Dict[str, Any]] = Field(None, description="聚合配置，null 表示禁用")


class StrategyResponse(BaseModel):
    """策略配置响应"""
    config: Optional[Dict[str, Any]] = None
    rule_id: Optional[int] = None


# ============ 多规则策略Schema ============

class StrategyRuleCreate(BaseModel):
    """策略规则创建（去重/抑制/聚合）"""
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    priority: int = Field(0, ge=0, le=1000)
    is_active: bool = True
    conditions: List[Condition] = []
    condition_mode: str = Field("and", pattern="^(and|or)$")
    config: Dict[str, Any] = Field(..., description="dedup/suppress/aggregate 配置")


class StrategyRuleUpdate(BaseModel):
    """策略规则更新"""
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    conditions: Optional[List[Condition]] = None
    condition_mode: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class StrategyRuleResponse(BaseModel):
    """策略规则响应"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    priority: int
    is_active: bool
    conditions: List[Condition] = []
    condition_mode: str = "and"
    config: Optional[Dict[str, Any]] = None
    match_count: int = 0
    last_match_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
