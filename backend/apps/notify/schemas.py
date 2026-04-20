"""
SentinelX - 通知Schema
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import re


# ============ 通知渠道Schema ============

class ChannelBase(BaseModel):
    """渠道基础Schema"""
    name: str = Field(..., min_length=1, max_length=128, description="渠道名称")
    code: str = Field(..., min_length=1, max_length=64, description="渠道代码")
    channel_type: str = Field(..., description="渠道类型")
    config: Dict[str, Any] = Field(default_factory=dict, description="渠道配置")
    is_active: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认渠道")


class ChannelCreate(ChannelBase):
    """创建渠道请求"""
    config: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('channel_type')
    @classmethod
    def validate_channel_type(cls, v: str) -> str:
        valid_types = {'dingtalk', 'feishu', 'wecom', 'email', 'webhook', 'slack'}
        if v not in valid_types:
            raise ValueError(f"channel_type must be one of: {', '.join(sorted(valid_types))}")
        return v

    @field_validator('config')
    @classmethod
    def validate_config(cls, v: Dict[str, Any], info) -> Dict[str, Any]:
        channel_type = info.data.get('channel_type')
        if not channel_type:
            return v
        return _validate_config_by_type(channel_type, v)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "钉钉告警群",
                "code": "dingtalk-alert",
                "channel_type": "dingtalk",
                "config": {"webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx"},
                "is_active": True,
                "is_default": False,
            }
        }


class ChannelUpdate(BaseModel):
    """更新渠道请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    code: Optional[str] = Field(None, min_length=1, max_length=64)
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

    @field_validator('config')
    @classmethod
    def validate_config(cls, v: Optional[Dict[str, Any]], info) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        channel_type = info.data.get('channel_type')
        if channel_type:
            return _validate_config_by_type(channel_type, v)
        return v


class ChannelResponse(ChannelBase):
    """渠道响应"""
    id: int
    tenant_id: str
    send_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    last_send_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChannelTypeInfo(BaseModel):
    """渠道类型信息"""
    value: str = Field(..., description="类型值")
    label: str = Field(..., description="显示名称")
    icon: str = Field(..., description="图标emoji")
    required_fields: List[str] = Field(default_factory=list, description="必填配置字段")
    optional_fields: List[str] = Field(default_factory=list, description="可选配置字段")
    description: str = Field("", description="描述")


class ChannelTypesResponse(BaseModel):
    """支持的渠道类型列表"""
    items: List[ChannelTypeInfo] = Field(default_factory=list)


def _validate_config_by_type(channel_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """根据渠道类型验证配置"""
    if channel_type == "dingtalk":
        if not config.get("webhook_url"):
            raise ValueError("dingtalk渠道必须配置 webhook_url")
        _validate_url(config["webhook_url"], "webhook_url")
    elif channel_type == "feishu":
        if not config.get("webhook_url"):
            raise ValueError("feishu渠道必须配置 webhook_url")
        _validate_url(config["webhook_url"], "webhook_url")
    elif channel_type == "wecom":
        if not config.get("webhook_url"):
            raise ValueError("wecom渠道必须配置 webhook_url")
        _validate_url(config["webhook_url"], "webhook_url")
    elif channel_type == "email":
        if not config.get("smtp_host"):
            raise ValueError("email渠道必须配置 smtp_host")
        if not config.get("username"):
            raise ValueError("email渠道必须配置 username")
        if not config.get("password"):
            raise ValueError("email渠道必须配置 password")
        if not config.get("from_addr"):
            raise ValueError("email渠道必须配置 from_addr")
        if not config.get("recipients"):
            raise ValueError("email渠道必须配置 recipients")
        if config.get("smtp_port"):
            port = int(config["smtp_port"])
            if port <= 0 or port > 65535:
                raise ValueError("smtp_port必须在1-65535范围内")
    elif channel_type == "webhook":
        if not config.get("webhook_url"):
            raise ValueError("webhook渠道必须配置 webhook_url")
        _validate_url(config["webhook_url"], "webhook_url")
    elif channel_type == "slack":
        if not config.get("webhook_url"):
            raise ValueError("slack渠道必须配置 webhook_url")
        _validate_url(config["webhook_url"], "webhook_url")
    return config


def _validate_url(value: str, field_name: str) -> None:
    """验证URL格式"""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if not url_pattern.match(value):
        raise ValueError(f"{field_name} 必须是有效的HTTP/HTTPS URL")


# ============ 测试发送Schema ============

class ChannelTestRequest(BaseModel):
    """测试发送请求"""
    content: Optional[str] = Field(
        None,
        description="测试消息内容，为空时使用默认内容"
    )


class ChannelTestResponse(BaseModel):
    """测试发送响应"""
    success: bool = Field(..., description="是否发送成功")
    error: Optional[str] = Field(None, description="错误信息")
    response_data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


# ============ 通知记录Schema ============

class NotificationRecordResponse(BaseModel):
    id: int
    tenant_id: str
    alert_id: int
    channel_id: int
    channel_type: str
    status: str
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """通知记录列表响应"""
    items: List[NotificationRecordResponse] = Field(default_factory=list)
    total: int = Field(0, description="总数")
    limit: int = Field(20, description="每页数量")
    offset: int = Field(0, description="偏移量")


# ============ 通知模板Schema ============

class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: Optional[str] = Field(None, min_length=1, max_length=64)
    channel_type: str = Field(..., description="适用渠道类型")
    content: str = Field(..., min_length=1, description="模板内容 (支持 Jinja2 变量)")
    variables: List[str] = Field(default_factory=list, description="变量列表")
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
