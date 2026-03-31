"""
SentinelX - 租户管理路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.core.database import get_db
from apps.core.security import hash_password, verify_password
from apps.auth.dependencies import get_current_user, get_current_tenant_id, get_token_payload, require_superuser
from apps.auth.services.auth import AuditService
from apps.tenant.models import Tenant, User, Role, Team, UserTenant, UserTeam
from apps.tenant.schemas import (
    TenantCreate, TenantUpdate, TenantResponse,
    UserCreate, UserUpdate, UserPasswordUpdate, UserResponse,
    RoleCreate, RoleUpdate, RoleResponse,
    TeamCreate, TeamUpdate, TeamResponse,
)

router = APIRouter()


# ============ 租户管理 ============

@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取租户列表（仅超级管理员或系统管理员）"""
    payload = get_token_payload()
    if not payload or not payload.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Superuser required")

    result = await db.execute(
        select(Tenant).where(Tenant.is_deleted == False).order_by(Tenant.id)
    )
    tenants = result.scalars().all()
    return tenants


@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    request: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建租户"""
    payload = get_token_payload()
    if not payload or not payload.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Superuser required")

    # 检查slug唯一性
    existing = await db.execute(
        select(Tenant).where(Tenant.slug == request.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    tenant = Tenant(
        name=request.name,
        slug=request.slug,
        config=request.config,
        max_alerts=request.max_alerts,
        max_users=request.max_users,
        max_rules=request.max_rules,
        max_channels=request.max_channels,
        alert_qps=request.alert_qps,
    )
    db.add(tenant)
    await db.flush()

    # 创建默认角色
    default_roles = [
        Role(tenant_id=tenant.id, name="管理员", code="admin", permissions=["*"], is_builtin=True, scope="tenant"),
        Role(tenant_id=tenant.id, name="观察者", code="viewer", permissions=["read", "alerts:read", "rules:read"], is_builtin=True, scope="tenant"),
    ]
    for role in default_roles:
        db.add(role)

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/tenants/current", response_model=TenantResponse)
async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """获取当前用户的租户信息"""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取租户详情"""
    payload = get_token_payload()
    is_superuser = payload.get("is_superuser", False) if payload else False
    is_system = payload.get("is_system", False) if payload else False
    current_tenant_id = payload.get("current_tenant_id") if payload else None

    # 系统管理员可以访问所有租户，租户管理员只能访问当前租户
    if not is_system and not is_superuser and current_tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    request: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新租户"""
    payload = get_token_payload()
    if not payload or not payload.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Superuser required")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant


# ============ 用户管理 ============

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前租户的用户列表"""
    result = await db.execute(
        select(User, UserTenant)
        .join(UserTenant, UserTenant.user_id == User.id)
        .where(
            UserTenant.tenant_id == tenant_id,
            User.is_deleted == False
        )
        .order_by(User.id)
    )
    rows = result.all()
    users = [user for user, _ in rows]
    return users


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建用户"""
    payload = get_token_payload()
    is_superuser = payload.get("is_superuser", False) if payload else False

    # 只能由租户管理员创建
    if not is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # 检查用户名唯一性
    existing = await db.execute(
        select(User).where(User.username == request.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    # 检查邮箱唯一性
    existing = await db.execute(
        select(User).where(User.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    # 获取默认角色
    role_result = await db.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.code == "viewer")
    )
    default_role = role_result.scalar_one_or_none()
    if not default_role:
        # 如果没有viewer角色，获取第一个可用角色
        role_result = await db.execute(
            select(Role).where(Role.tenant_id == tenant_id).order_by(Role.id)
        )
        default_role = role_result.scalar_one_or_none()

    user = User(
        username=request.username,
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),
        is_system=False,
        is_superuser=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # 创建用户-租户关联
    user_tenant = UserTenant(
        user_id=user.id,
        tenant_id=tenant_id,
        role_id=default_role.id if default_role else None,
        is_current=True,
    )
    db.add(user_tenant)

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取用户详情"""
    result = await db.execute(
        select(User)
        .join(UserTenant, UserTenant.user_id == User.id)
        .where(
            User.id == user_id,
            UserTenant.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新用户"""
    result = await db.execute(
        select(User)
        .join(UserTenant, UserTenant.user_id == User.id)
        .where(
            User.id == user_id,
            UserTenant.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        if field != "password":
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}/password")
async def change_password(
    user_id: int,
    request: UserPasswordUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改密码"""
    payload = get_token_payload()
    is_superuser = payload.get("is_superuser", False) if payload else False

    # 只能修改自己的密码，或者管理员可以修改其他用户密码
    if current_user.id != user_id and not is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(User)
        .join(UserTenant, UserTenant.user_id == User.id)
        .where(
            User.id == user_id,
            UserTenant.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.old_password and not verify_password(request.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password incorrect")

    user.password_hash = hash_password(request.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}


# ============ 角色管理 ============

@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取角色列表（包含系统级角色和当前租户的角色）"""
    result = await db.execute(
        select(Role).where(
            (Role.tenant_id == tenant_id) | (Role.tenant_id == None)
        ).order_by(Role.scope, Role.is_builtin.desc(), Role.id)
    )
    return result.scalars().all()


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    request: RoleCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建角色"""
    role = Role(
        tenant_id=tenant_id,
        name=request.name,
        code=request.code,
        description=request.description,
        permissions=request.permissions,
        scope="tenant",
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role
