"""
SentinelX - 租户管理路由
"""
import secrets
from datetime import datetime
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
    UserCreate, UserUpdate, UserPasswordUpdate, UserResponse, UserRoleUpdate,
    RoleCreate, RoleUpdate, RoleResponse,
    TeamCreate, TeamUpdate, TeamResponse,
    PublicTenantResponse,
    UserPendingResponse, UserApproveRequest, UserRejectRequest,
)

router = APIRouter()


# ============ 公开接口（无需认证） ============

@router.get("/tenants/public", response_model=list[PublicTenantResponse])
async def list_public_tenants(
    db: AsyncSession = Depends(get_db),
):
    """获取公开租户列表（用于用户注册，无需认证）"""
    result = await db.execute(
        select(Tenant).where(
            Tenant.is_deleted == False,
            Tenant.is_active == True
        ).order_by(Tenant.id)
    )
    tenants = result.scalars().all()
    return tenants


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

    await db.flush()

    # 获取管理员角色
    admin_role = await db.execute(
        select(Role).where(Role.tenant_id == tenant.id, Role.code == "admin")
    )
    admin_role_obj = admin_role.scalar_one_or_none()

    # 将创建者（系统管理员）添加到新租户
    user_tenant = UserTenant(
        user_id=current_user.id,
        tenant_id=tenant.id,
        role_id=admin_role_obj.id if admin_role_obj else None,
        is_current=False,
    )
    db.add(user_tenant)

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

    # 构建响应，包含 webhook_url
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "config": tenant.config,
        "api_token": tenant.api_token,
        "webhook_api_key": tenant.webhook_api_key,
        "max_alerts": tenant.max_alerts,
        "max_users": tenant.max_users,
        "max_rules": tenant.max_rules,
        "max_channels": tenant.max_channels,
        "alert_qps": tenant.alert_qps,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
        "webhook_url": f"/api/v1/webhooks/{tenant.slug}" if tenant.slug else None,
    }


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


# ============ Webhook Key 管理 ============

@router.post("/tenants/{tenant_id}/webhook-key")
async def generate_webhook_key(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成或重置租户的 Webhook API Key"""
    payload = get_token_payload()
    is_superuser = payload.get("is_superuser", False) if payload else False

    # 只有管理员可以操作
    if not is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # 生成新的 API Key (明文，用于返回给用户一次)
    raw_api_key = f"wh_{secrets.token_urlsafe(32)}"
    tenant.webhook_api_key = hash_password(raw_api_key)
    await db.commit()

    # 返回完整的 Webhook URL 和 API Key
    webhook_base_url = f"/api/v1/webhooks/{tenant.slug}"
    return {
        "webhook_url": webhook_base_url,
        "webhook_url_template": f"{webhook_base_url}/{{source_type}}",
        "api_key": raw_api_key,
        "message": "Store the API key securely. It will not be shown again.",
    }


@router.get("/tenants/{tenant_id}/webhook-key")
async def get_webhook_key_info(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取租户的 Webhook URL 信息（不包含 API Key）"""
    payload = get_token_payload()
    is_superuser = payload.get("is_superuser", False) if payload else False

    # 只有管理员可以查看
    if not is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    webhook_base_url = f"/api/v1/webhooks/{tenant.slug}"
    return {
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "webhook_url": webhook_base_url,
        "webhook_url_template": f"{webhook_base_url}/{{source_type}}",
        "has_api_key": bool(tenant.webhook_api_key),
    }


# ============ 系统管理员用户管理 ============

@router.get("/admin/users/pending", response_model=list[UserPendingResponse])
async def list_pending_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有待审批用户（仅系统管理员）"""
    if not current_user.is_system:
        raise HTTPException(status_code=403, detail="System admin required")

    result = await db.execute(
        select(User, UserTenant, Tenant)
        .outerjoin(UserTenant, (UserTenant.user_id == User.id) & (UserTenant.is_primary == True))
        .outerjoin(Tenant, Tenant.id == UserTenant.tenant_id)
        .where(
            User.is_deleted == False,
            User.is_approved == False
        )
        .order_by(User.created_at.desc())
    )
    rows = result.all()

    pending_users = []
    for user, user_tenant, tenant in rows:
        pending_users.append(UserPendingResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            requested_tenant_id=tenant.id if tenant else None,
            requested_tenant_name=tenant.name if tenant else None,
            created_at=user.created_at,
        ))
    return pending_users


@router.post("/admin/users/{user_id}/approve")
async def approve_user(
    user_id: int,
    request: UserApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审批通过用户（仅系统管理员）"""
    if not current_user.is_system:
        raise HTTPException(status_code=403, detail="System admin required")

    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_approved:
        raise HTTPException(status_code=400, detail="User already approved")

    # 验证系统级角色（如果有）
    if request.system_role_id:
        result = await db.execute(select(Role).where(Role.id == request.system_role_id))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="System role not found")
        if role.tenant_id is not None:
            raise HTTPException(status_code=400, detail="System role must be a system-level role")

    # 验证租户角色
    for tr in request.tenant_roles:
        result = await db.execute(select(Role).where(Role.id == tr.role_id))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail=f"Tenant role {tr.role_id} not found")
        if role.tenant_id is None:
            raise HTTPException(status_code=400, detail="Tenant role must be a tenant-level role")

        result = await db.execute(select(Tenant).where(Tenant.id == tr.tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant {tr.tenant_id} not found")

    # 更新用户审批状态
    user.is_approved = True
    user.is_active = True
    user.approved_at = datetime.utcnow()
    user.approved_by = current_user.id

    # 如果有系统级角色，更新用户并自动分配所有租户
    if request.system_role_id:
        user.is_system = True

        # 获取用户注册时申请的租户（如果有）
        result = await db.execute(
            select(UserTenant).where(UserTenant.user_id == user_id)
        )
        requested_tenant = result.scalars().first()

        # 为系统管理员自动分配所有活跃租户
        result = await db.execute(
            select(Tenant).where(Tenant.is_active == True, Tenant.is_deleted == False)
        )
        all_tenants = result.scalars().all()

        # 获取系统管理员角色（tenant_admin）用于分配给各租户
        result = await db.execute(
            select(Role).where(Role.code == "tenant_admin", Role.tenant_id.isnot(None))
        )
        tenant_admin_role = result.scalars().first()

        for idx, tenant in enumerate(all_tenants):
            # 检查是否已存在关联
            result = await db.execute(
                select(UserTenant).where(
                    UserTenant.user_id == user_id,
                    UserTenant.tenant_id == tenant.id
                )
            )
            existing_ut = result.scalar_one_or_none()

            if existing_ut:
                # 更新已有关联的角色为租户管理员
                if tenant_admin_role:
                    existing_ut.role_id = tenant_admin_role.id
                existing_ut.is_primary = (requested_tenant and requested_tenant.tenant_id == tenant.id) or (idx == 0 and not requested_tenant)
            else:
                # 创建新关联，使用租户管理员角色
                new_ut = UserTenant(
                    user_id=user_id,
                    tenant_id=tenant.id,
                    role_id=tenant_admin_role.id if tenant_admin_role else tr.role_id if request.tenant_roles else 1,
                    is_current=(requested_tenant and requested_tenant.tenant_id == tenant.id) or (idx == 0 and not requested_tenant),
                    is_primary=(requested_tenant and requested_tenant.tenant_id == tenant.id) or (idx == 0 and not requested_tenant),
                )
                db.add(new_ut)

    # 处理租户角色关联（仅非系统级角色时）
    elif request.tenant_roles:
        # 获取用户注册时申请的租户（如果有）
        result = await db.execute(
            select(UserTenant).where(UserTenant.user_id == user_id)
        )
        requested_tenant = result.scalars().first()

        for idx, tr in enumerate(request.tenant_roles):
            # 检查是否已存在关联
            result = await db.execute(
                select(UserTenant).where(
                    UserTenant.user_id == user_id,
                    UserTenant.tenant_id == tr.tenant_id
                )
            )
            existing_ut = result.scalar_one_or_none()

            if existing_ut:
                existing_ut.role_id = tr.role_id
                existing_ut.is_primary = (idx == 0) or (requested_tenant and requested_tenant.tenant_id == tr.tenant_id)
            else:
                new_ut = UserTenant(
                    user_id=user_id,
                    tenant_id=tr.tenant_id,
                    role_id=tr.role_id,
                    is_current=(idx == 0) or (requested_tenant and requested_tenant.tenant_id == tr.tenant_id),
                    is_primary=(idx == 0) or (requested_tenant and requested_tenant.tenant_id == tr.tenant_id),
                )
                db.add(new_ut)
    else:
        # 既没有系统级角色也没有租户角色，报错
        raise HTTPException(status_code=400, detail="At least one of system_role_id or tenant_roles is required")

    await db.commit()

    return {
        "message": "User approved",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_approved": user.is_approved,
            "is_active": user.is_active,
            "is_system": user.is_system,
        }
    }


@router.post("/admin/users/{user_id}/reject")
async def reject_user(
    user_id: int,
    request: UserRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """拒绝用户注册（仅系统管理员）"""
    if not current_user.is_system:
        raise HTTPException(status_code=403, detail="System admin required")

    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_approved:
        raise HTTPException(status_code=400, detail="User already approved, cannot reject")

    # 删除用户
    user.is_deleted = True
    await db.commit()

    return {"message": "User rejected"}


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
        is_approved=True,  # 管理员创建的用户默认已审批
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


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户在指定租户的角色"""
    # 检查是否是租户管理员或系统管理员
    if not current_user.is_system and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 处理每个租户角色
    for tr in request.tenant_roles:
        # 检查角色是否存在且属于指定租户
        result = await db.execute(
            select(Role).where(
                Role.id == tr.role_id,
                Role.tenant_id == tr.tenant_id
            )
        )
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail=f"Role {tr.role_id} not found in tenant {tr.tenant_id}")

        # 检查目标用户是否属于指定租户
        result = await db.execute(
            select(UserTenant).where(
                UserTenant.user_id == user_id,
                UserTenant.tenant_id == tr.tenant_id
            )
        )
        user_tenant = result.scalar_one_or_none()

        if user_tenant:
            # 更新已存在关联的角色
            user_tenant.role_id = tr.role_id
        else:
            # 创建新关联
            new_ut = UserTenant(
                user_id=user_id,
                tenant_id=tr.tenant_id,
                role_id=tr.role_id,
                is_current=True,
                is_primary=True,
            )
            db.add(new_ut)

    await db.commit()

    return {"message": "Role updated successfully"}


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


@router.delete("/users/{user_id}")
async def remove_user_from_tenant(
    user_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从本租户移除用户（仅管理员）"""
    payload = get_token_payload()
    is_superuser = payload.get("is_superuser", False) if payload else False

    if not is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # 获取用户在本租户的关联
    result = await db.execute(
        select(UserTenant).where(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id
        )
    )
    user_tenant = result.scalar_one_or_none()
    if not user_tenant:
        raise HTTPException(status_code=404, detail="User not found in this tenant")

    # 不能移除自己
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    # 删除关联
    await db.delete(user_tenant)
    await db.commit()

    return {"message": "User removed from tenant"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    is_active: bool,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """激活/禁用用户（仅管理员）"""
    payload = get_token_payload()
    is_superuser = payload.get("is_superuser", False) if payload else False

    if not is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # 获取用户
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

    # 不能禁用自己
    if current_user.id == user_id and not is_active:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")

    user.is_active = is_active
    await db.commit()

    return {
        "message": f"User {'activated' if is_active else 'deactivated'}",
        "is_active": user.is_active
    }


# ============ 角色管理 ============

@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色列表（包含系统级角色和当前租户的角色）"""
    # 系统管理员可以查看所有角色
    if current_user.is_system:
        result = await db.execute(
            select(Role).order_by(Role.scope, Role.is_builtin.desc(), Role.id)
        )
    else:
        # 非系统管理员只能查看系统级角色
        result = await db.execute(
            select(Role).where(Role.tenant_id == None).order_by(Role.scope, Role.is_builtin.desc(), Role.id)
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
