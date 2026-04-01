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
    webhook_api_key: Optional[str] = None  # 不返回给前端，只用于内部
    max_alerts: int
    max_users: int
    max_rules: int
    max_channels: int
    alert_qps: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    webhook_url: Optional[str] = None  # Webhook URL 前缀

    class Config:
        from_attributes = True


# ============ 用户Schema ============

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    # tenant_id 不需要，前端自动使用当前租户


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    old_password: Optional[str] = None  # 管理员修改时不需要旧密码
    new_password: str = Field(..., min_length=8, max_length=128)


class UserRoleUpdate(BaseModel):
    """更新用户角色"""
    tenant_roles: List["TenantRoleInput"] = Field(default=[], description="租户角色列表")


class TenantRoleInput(BaseModel):
    """租户角色输入"""
    tenant_id: int
    role_id: int


class UserResponse(UserBase):
    id: int
    email: str  # 覆盖 UserBase 的 EmailStr，使用字符串以支持内部邮箱
    is_system: bool  # 系统管理员标志
    is_superuser: bool  # 保留但废弃，由UserTenant决定
    is_active: bool
    is_approved: bool  # 审批状态
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserPendingResponse(BaseModel):
    """待审批用户信息"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    requested_tenant_id: Optional[int] = None
    requested_tenant_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserApproveRequest(BaseModel):
    """审批用户请求"""
    system_role_id: Optional[int] = Field(None, description="系统级角色ID（可选）")
    tenant_roles: List["TenantRoleInput"] = Field(default=[], description="租户角色列表")


class TenantRoleInput(BaseModel):
    """租户角色输入"""
    tenant_id: int
    role_id: int


class UserRejectRequest(BaseModel):
    """拒绝用户请求"""
    reason: Optional[str] = None


class PublicTenantResponse(BaseModel):
    """公开租户信息"""
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True
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
    scope: Optional[str] = "tenant"  # system 或 tenant
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
