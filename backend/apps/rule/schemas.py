"""
SentinelX - 规则Schema
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ 规则条件Schema ============

class Condition(BaseModel):
    """规则条件"""
    field: str = Field(..., description="字段路径，如 severity/labels.cluster")
    operator: str = Field(..., description="操作符: eq/ne/gt/gte/lt/lte/contains/regex/in/not_in")
    value: Any = Field(..., description="比较值")


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
