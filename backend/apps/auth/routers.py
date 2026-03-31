"""
SentinelX - 认证路由
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.database import get_db
from apps.core.security import verify_token
from apps.core.exceptions import AuthenticationError
from apps.tenant.models import User
from apps.auth.schemas import LoginRequest, TokenResponse, RefreshTokenRequest, RegisterRequest
from apps.auth.services.auth import AuthService, PermissionService
from apps.auth.dependencies import (
    get_current_user,
    get_current_tenant_id,
    get_permission_service,
    get_audit_service,
)
from apps.auth.api_key import APIKeyAuth

router = APIRouter()


# ============ 用户认证 ============

@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    auth_service = AuthService(db)

    try:
        user, access_token, refresh_token = await auth_service.authenticate(
            request.username,
            request.password
        )

        # 记录审计日志
        audit_service = auth_service
        from apps.auth.services import AuditService
        audit = AuditService(db)
        await audit.log(
            tenant_id=user.tenant_id,
            user_id=user.id,
            username=user.username,
            action="login",
            resource_type="auth",
            ip_address=_get_client_ip(http_request),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message),
        )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """刷新令牌"""
    auth_service = AuthService(db)

    try:
        access_token, refresh_token = await auth_service.refresh_tokens(
            request.refresh_token
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message),
        )


@router.post("/auth/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    # 检查用户名是否已存在
    existing = await db.execute(
        select(User).where(User.username == request.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    # 检查邮箱是否已存在
    existing = await db.execute(
        select(User).where(User.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    # 创建用户
    user = User(
        tenant_id=request.tenant_id,
        username=request.username,
        email=request.email,
        phone=request.phone,
        password_hash=AuthService(db)._hash_password(request.password),  # TODO: 修复
    )

    # TODO: 默认角色分配

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "tenant_id": user.tenant_id,
    }


@router.get("/auth/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户信息"""
    permission_service = PermissionService(db)
    permissions = await permission_service.get_user_permissions(current_user.id)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "is_superuser": current_user.is_superuser,
        "permissions": permissions,
    }


@router.get("/auth/permissions")
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户权限"""
    permission_service = PermissionService(db)
    permissions = await permission_service.get_user_permissions(current_user.id)

    return {
        "permissions": permissions,
    }


# ============ API Key管理 ============

@router.post("/auth/api-keys")
async def create_api_key(
    name: str,
    expires_days: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建API Key (仅管理员)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    api_key_auth = APIKeyAuth(db)
    api_key, full_api_key = await api_key_auth.create_api_key(
        tenant_id=current_user.tenant_id,
        name=name,
        expires_days=expires_days,
    )

    # 返回完整API Key (只显示一次)
    return {
        "api_key": api_key,
        "full_api_key": full_api_key,
        "message": "Store the full API key securely. It will not be shown again.",
    }


@router.get("/auth/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出API Key (不包含secret)"""
    api_key_auth = APIKeyAuth(db)
    keys = await api_key_auth.list_api_keys(current_user.tenant_id)
    return {"api_keys": keys}


@router.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤销API Key"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    api_key_auth = APIKeyAuth(db)
    success = await api_key_auth.revoke_api_key(current_user.tenant_id, key_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found",
        )

    return {"message": "API Key revoked successfully"}


# ============ 辅助函数 ============

def _get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"
