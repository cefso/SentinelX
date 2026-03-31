"""
SentinelX - 租户管理路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.core.database import get_db
from apps.core.security import hash_password, verify_password
from apps.auth.routers import get_current_user, get_current_tenant_id
from apps.tenant.models import Tenant, User, Role, Team, UserRole, UserTeam
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
    """获取租户列表（仅超级管理员）"""
    if not current_user.is_superuser:
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
    if not current_user.is_superuser:
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
        Role(tenant_id=tenant.id, name="管理员", code="admin", permissions=["*"], is_builtin=True),
        Role(tenant_id=tenant.id, name="观察者", code="viewer", permissions=["read"], is_builtin=True),
    ]
    for role in default_roles:
        db.add(role)

    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取租户详情"""
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
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
    if not current_user.is_superuser:
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
    """获取用户列表"""
    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.is_deleted == False
        ).order_by(User.id)
    )
    return result.scalars().all()


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建用户"""
    # 检查配额
    user_count = await db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant_id,
            User.is_deleted == False
        )
    )

    # 检查用户名唯一性
    existing = await db.execute(
        select(User).where(User.username == request.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        tenant_id=tenant_id,
        username=request.username,
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),
    )
    db.add(user)
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
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id
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
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in request.model_dump(exclude_unset=True).items():
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
    # 只能修改自己的密码，或者管理员可以修改其他用户密码
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(request.old_password, user.password_hash):
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
    """获取角色列表"""
    result = await db.execute(
        select(Role).where(
            (Role.tenant_id == tenant_id) | (Role.tenant_id == None)
        ).order_by(Role.is_builtin.desc(), Role.id)
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
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role
