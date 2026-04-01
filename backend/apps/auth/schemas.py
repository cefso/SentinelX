"""
SentinelX - 认证相关Schema
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class RoleInfo(BaseModel):
    """角色信息"""
    id: int
    code: str
    name: str


class TenantInfo(BaseModel):
    """租户信息"""
    id: int
    name: str
    slug: str
    role: RoleInfo
    is_current: bool
    is_superuser: bool
    permissions: List[str]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 过期时间(秒)
    user: Optional[dict] = None  # 用户信息
    tenants: Optional[List[TenantInfo]] = None  # 租户列表


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SwitchTenantRequest(BaseModel):
    """切换租户请求"""
    tenant_id: int = Field(..., gt=0)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=256)
    password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = None
    tenant_id: Optional[int] = None  # 注册时申请的租户ID


class TokenPayload(BaseModel):
    sub: int  # user_id
    user_id: int
    username: str
    current_tenant_id: int
    is_system: bool = False
    is_superuser: bool = False
    permissions: List[str] = []
    exp: int
    type: str  # access / refresh
