"""
SentinelX - 通用响应模型与枚举常量
减少手工 dict 端点的契约漂移，并统一状态/级别魔法字符串。
"""
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"
    DEDUPLICATED = "deduplicated"
    AGGREGATED = "aggregated"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MessageResponse(BaseModel):
    message: str


class IdMessageResponse(BaseModel):
    id: int
    message: str = "ok"


T = TypeVar("T")


class ListEnvelope(BaseModel, Generic[T]):
    """通用列表信封：items + 可选 total/page/page_size"""
    items: List[T]
    total: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = None


class APIKeyItem(BaseModel):
    key_id: str
    name: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool = True
    created_by: Optional[int] = None


class APIKeyListResponse(BaseModel):
    api_keys: List[APIKeyItem]


class APIKeyCreateResponse(BaseModel):
    api_key: str
    full_api_key: str
    message: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[dict] = None
    tenants: Optional[List[dict]] = None


class CurrentUserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_system: bool = False
    is_superuser: bool = False
    current_tenant_id: Optional[int] = None
    tenants: Optional[List[dict]] = None
    permissions: Optional[List[str]] = None


class PermissionsResponse(BaseModel):
    permissions: List[str] = Field(default_factory=list)
    is_superuser: bool = False
    is_system: bool = False
