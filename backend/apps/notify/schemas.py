"""
SentinelX - 通知Schema
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import ipaddress
import re
from urllib.parse import urlparse


# ============ 渠道 config 脱敏 ============

# 敏感字段名（子串匹配，大小写不敏感）
_SENSITIVE_KEY_PARTS = ("password", "secret", "token", "access_key", "api_key")
# 非敏感标识类字段：只展示尾部
_MASK_TAIL_KEYS = ("access_key_id",)
# URL 类字段：保留 scheme+host，路径/查询脱敏
_URL_KEYS = ("webhook_url", "callback_url", "url")

MASK_PLACEHOLDER = "***"


def _mask_keep_tail(value: str, tail: int = 4) -> str:
    """显示尾部若干字符，前面用 *** 替换。"""
    if not value:
        return MASK_PLACEHOLDER
    if len(value) <= tail:
        return MASK_PLACEHOLDER
    return f"{MASK_PLACEHOLDER}{value[-tail:]}"


def _mask_url(value: str) -> str:
    """保留 scheme://host，路径与查询替换为 ***。"""
    try:
        parsed = urlparse(value)
    except Exception:
        return MASK_PLACEHOLDER
    if not parsed.scheme or not parsed.netloc:
        return MASK_PLACEHOLDER
    return f"{parsed.scheme}://{parsed.netloc}/{MASK_PLACEHOLDER}"


def _is_sensitive_key(key: str) -> bool:
    lk = key.lower()
    if lk in _MASK_TAIL_KEYS:
        return False
    return any(part in lk for part in _SENSITIVE_KEY_PARTS)


def mask_channel_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """对外响应时脱敏渠道 config 中的敏感字段。"""
    if not config or not isinstance(config, dict):
        return {}
    masked: Dict[str, Any] = {}
    for key, value in config.items():
        lk = str(key).lower()
        if not isinstance(value, str):
            masked[key] = value
            continue
        if lk in _URL_KEYS:
            masked[key] = _mask_url(value)
        elif lk in _MASK_TAIL_KEYS or (lk.endswith("_id") and "access_key" in lk):
            masked[key] = _mask_keep_tail(value)
        elif _is_sensitive_key(lk):
            masked[key] = MASK_PLACEHOLDER
        else:
            masked[key] = value
    return masked


def is_masked_value(value: Any) -> bool:
    """判断提交值是否仍为脱敏占位（未被用户改写）。"""
    return isinstance(value, str) and MASK_PLACEHOLDER in value


def restore_masked_config(
    original: Optional[Dict[str, Any]],
    incoming: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """更新时：若字段值仍含 ***，用库中原值覆盖，避免抹掉密钥。"""
    restored: Dict[str, Any] = dict(incoming or {})
    original = original or {}
    for key, value in list(restored.items()):
        if is_masked_value(value):
            if key in original and original[key] is not None:
                restored[key] = original[key]
            else:
                # 无原值可回填时丢弃该字段，防止写入占位符
                del restored[key]
    return restored


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
        valid_types = {'dingtalk', 'feishu', 'wecom', 'email', 'webhook', 'slack', 'aliyun_voice'}
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
    """渠道响应（config 敏感字段脱敏）"""
    id: int
    tenant_id: int
    send_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    last_send_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("config", mode="before")
    @classmethod
    def _mask_sensitive_config(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, dict):
            return mask_channel_config(v)
        return v or {}

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
    elif channel_type == "aliyun_voice":
        if not config.get("access_key_id"):
            raise ValueError("aliyun_voice渠道必须配置 access_key_id")
        if not config.get("access_key_secret"):
            raise ValueError("aliyun_voice渠道必须配置 access_key_secret")
        if not config.get("called_number"):
            raise ValueError("aliyun_voice渠道必须配置 called_number")
        if not config.get("template_code"):
            raise ValueError("aliyun_voice渠道必须配置 template_code")
    return config


def _is_blocked_host(host: str) -> bool:
    """基础 SSRF 拦截：拒绝本机/内网/链路本地等地址"""
    if not host:
        return True
    host = host.strip().lower()
    # 去掉 IPv6 方括号
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if host in {"localhost", "localhost.localdomain", "0.0.0.0", "::1", "0:0:0:0:0:0:0:1"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # 非 IP 字面量（域名），不做 DNS 解析，放行
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    )


def _validate_url(value: str, field_name: str) -> None:
    """验证URL格式并做基础 SSRF 拦截"""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
        r'\[[0-9a-fA-F:.]+\])'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if not url_pattern.match(value):
        raise ValueError(f"{field_name} 必须是有效的HTTP/HTTPS URL")

    parsed = urlparse(value)
    if _is_blocked_host(parsed.hostname or ""):
        raise ValueError(f"{field_name} 不允许指向本机或内网地址")


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
    tenant_id: int
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
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
