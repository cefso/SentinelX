"""
SentinelX - 认证依赖注入
"""
from typing import Optional
from fastapi import Depends, HTTPException, Header, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.database import get_db
from apps.core.security import verify_token
from apps.tenant.models import User
from apps.auth.services.auth import AuthService, PermissionService, AuditService
from apps.auth.api_key import APIKeyAuth
from apps.core.exceptions import AuthenticationError, AuthorizationError


# 全局变量存储当前请求的token payload
# 在生产环境中应使用 request.state 或 contextvars
_token_payload: Optional[dict] = None


def set_token_payload(payload: dict):
    """设置当前请求的token payload"""
    global _token_payload
    _token_payload = payload


def get_token_payload() -> dict:
    """获取当前请求的token payload"""
    return _token_payload


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
) -> int:
    """获取当前租户ID"""
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
    return tenant_id


def require_permission(permission: str):
    """
    权限检查装饰器
    用法:
        @router.get("/alerts")
        @require_permission("alerts:read")
        async def get_alerts(current_user: User = Depends(get_current_user)):
            ...
    """
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        payload = get_token_payload()
        permissions = payload.get("permissions", []) if payload else []

        # 检查是否有权限
        if "*" in permissions or permission in permissions:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission}",
        )

    return dependency


def require_superuser():
    """超级管理员检查"""
    async def dependency(current_user: User = Depends(get_current_user)):
        payload = get_token_payload()
        is_superuser = payload.get("is_superuser", False) if payload else False

        if not is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser access required",
            )
        return current_user

    return dependency
