"""
SentinelX - 认证依赖注入
"""
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import get_db
from apps.core.security import verify_token
from apps.tenant.models import User
from apps.auth.services.auth import AuthService, PermissionService, AuditService
from apps.auth.api_key import APIKeyAuth
from apps.core.exceptions import AuthenticationError, AuthorizationError


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
        # 创建系统用户对象用于权限检查
        system_user = User(
            id=0,
            tenant_id=tenant.id,
            username=f"api_key:{tenant.slug}",
            is_superuser=True,  # API Key默认有全部权限
        )
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

    user_id = payload.get("sub")
    if not user_id:
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
) -> int:
    """获取当前租户ID"""
    return current_user.tenant_id


def require_permission(permission: str):
    """
    权限检查装饰器
    用法:
        @router.get("/alerts")
        @require_permission("alert:read")
        async def get_alerts(current_user: User = Depends(get_current_user)):
            ...
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        permission_service = PermissionService(db)
        has_permission = await permission_service.check_permission(
            current_user.id, permission
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )

        return current_user

    return dependency


def require_superuser():
    """超级管理员检查"""
    async def dependency(current_user: User = Depends(get_current_user)):
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser access required",
            )
        return current_user

    return dependency
