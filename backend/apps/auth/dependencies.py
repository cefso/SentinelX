"""
SentinelX - 认证依赖注入
"""
import contextvars
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.database import get_db
from apps.core.security import verify_token
from apps.tenant.models import User
from apps.auth.services.auth import AuthService, PermissionService, AuditService
from apps.auth.api_key import APIKeyAuth


# 使用 ContextVar 替代全局变量，避免异步并发竞态条件
_token_payload_var: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar('token_payload', default=None)



def set_token_payload(payload: dict):
    """设置当前请求的token payload"""
    _token_payload_var.set(payload)


def get_token_payload() -> Optional[dict]:
    """获取当前请求的token payload"""
    return _token_payload_var.get()


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """获取认证服务"""
    return AuthService(db)


async def get_permission_service(
    db: AsyncSession = Depends(get_db),
) -> PermissionService:
    """获取权限服务"""
    return PermissionService(db)


async def get_audit_service(
    db: AsyncSession = Depends(get_db),
) -> AuditService:
    """获取审计服务"""
    return AuditService(db)


async def get_api_key_auth(
    db: AsyncSession = Depends(get_db),
) -> APIKeyAuth:
    """获取API Key认证服务"""
    return APIKeyAuth(db)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前用户
    支持两种认证方式:
    1. JWT Bearer Token
    2. API Key
    """
    # 优先使用API Key认证 (Agent场景)
    if x_api_key:
        api_key_auth = APIKeyAuth(db)
        tenant = await api_key_auth.verify_api_key(x_api_key)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )

        # API Key认证返回虚拟用户（系统用户）
        # API Key 有全部权限，设置 is_superuser=True
        system_user = User(
            id=0,
            username=f"api_key:{tenant.slug}",
            email="",
            password_hash="",
            is_system=False,
            is_superuser=True,  # API Key默认有全部权限
            is_active=True,
        )
        # 设置token payload用于API Key场景
        set_token_payload({
            "user_id": 0,
            "username": f"api_key:{tenant.slug}",
            "current_tenant_id": tenant.id,
            "is_system": False,
            "is_superuser": True,
            "permissions": ["*"],
        })
        return system_user

    # JWT认证
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format",
        )

    token = authorization[7:]
    payload = verify_token(token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # 保存token payload供后续使用
    set_token_payload(payload)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # JWT user_id 是整数
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    """获取当前租户ID（统一为 int，与 tenants.id 一致）"""
    payload = get_token_payload()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    tenant_id = payload.get("current_tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenant context",
        )

    tenant_id = int(tenant_id)

    # 检查租户是否被禁用
    from apps.tenant.models import Tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive or not found",
        )

    return tenant_id


def require_permission(permission: str):
    """
    权限检查依赖 —— 以 DB 为权威来源。

    用法:
        @router.get("/alerts")
        async def get_alerts(current_user: User = Depends(require_permission("alerts:read"))):
            ...

    支持通配符:
        - "read" 匹配所有 ":read" 结尾的权限
        - "admin" 或 "*" 匹配所有权限

    说明:
        JWT claim 中的 permissions 仅作历史兼容，不再作为放行依据。
        角色降权 / 权限回收后，即使旧 token 仍在有效期内也会立即被拒绝。
    """
    async def _check_permission(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # API Key 虚拟用户（user_id=0）：密钥本身即凭证，保留全量权限
        if current_user.id == 0:
            return current_user

        payload = get_token_payload() or {}
        tenant_id = payload.get("current_tenant_id")
        try:
            tenant_id = int(tenant_id) if tenant_id is not None else None
        except (TypeError, ValueError):
            tenant_id = None

        # is_system 已由 get_current_user 从 DB User 加载，以 DB 字段为准
        permission_service = PermissionService(db)
        authz = await permission_service.get_user_tenant_authz(
            user_id=current_user.id,
            tenant_id=tenant_id,
            is_system=bool(current_user.is_system),
        )

        if not permission_service.match_permission(authz["permissions"], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return current_user

    return _check_permission


def require_superuser():
    """
    超级管理员检查 —— 以 DB 为权威来源。

    - User.is_system 以 DB 字段为准（get_current_user 已查库）
    - 租户超级用户以 Role.code / Role.permissions 为准（DB 查询）
    - JWT claim 中的 is_superuser 不再作为放行依据
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # API Key 虚拟用户：认证层已校验密钥
        if current_user.id == 0:
            return current_user

        # 系统管理员以 DB User.is_system 为准
        if current_user.is_system:
            return current_user

        payload = get_token_payload() or {}
        tenant_id = payload.get("current_tenant_id")
        try:
            tenant_id = int(tenant_id) if tenant_id is not None else None
        except (TypeError, ValueError):
            tenant_id = None

        authz = await PermissionService(db).get_user_tenant_authz(
            user_id=current_user.id,
            tenant_id=tenant_id,
            is_system=False,
        )

        if not authz["is_superuser"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser access required",
            )
        return current_user

    return dependency
