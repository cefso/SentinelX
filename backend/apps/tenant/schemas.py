"""
SentinelX - 租户管理Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ============ 租户Schema ============

class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")


class TenantCreate(TenantBase):
    config: Optional[dict] = {}
    max_alerts: Optional[int] = 10000
    max_users: Optional[int] = 10
    max_rules: Optional[int] = 100
    max_channels: Optional[int] = 20
    alert_qps: Optional[int] = 100


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    config: Optional[dict] = None
    max_alerts: Optional[int] = None
    max_users: Optional[int] = None
    max_rules: Optional[int] = None
    max_channels: Optional[int] = None
    alert_qps: Optional[int] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    id: int
    api_token: Optional[str] = None
    max_alerts: int
    max_users: int
    max_rules: int
    max_channels: int
    alert_qps: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 用户Schema ============

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    tenant_id: int


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    id: int
    tenant_id: int
    is_superuser: bool
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 角色Schema ============

class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permissions: List[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(RoleBase):
    id: int
    tenant_id: Optional[int]
    permissions: List[str]
    is_builtin: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ 团队Schema ============

class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    code: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    leader_id: Optional[int] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    leader_id: Optional[int] = None


class TeamResponse(TeamBase):
    id: int
    tenant_id: int
    leader_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
