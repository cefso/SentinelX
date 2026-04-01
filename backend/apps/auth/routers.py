"""
SentinelX - 认证路由
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.database import get_db
from apps.core.security import verify_token
from apps.core.exceptions import AuthenticationError
from apps.tenant.models import User
from apps.auth.schemas import (
    LoginRequest, TokenResponse, RefreshTokenRequest, RegisterRequest,
    SwitchTenantRequest, TenantInfo
)
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
        user, access_token, refresh_token, tenants = await auth_service.authenticate(
            request.username,
            request.password
        )

        # 获取当前租户信息
        current_tenant = next((t for t in tenants if t["is_current"]), None)

        # 记录审计日志
        if current_tenant:
            from apps.auth.services.auth import AuditService
            audit = AuditService(db)
            await audit.log(
                tenant_id=str(current_tenant["id"]),
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
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_system": user.is_system,
            },
            tenants=tenants,
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
    """用户注册（需管理员审批）"""
    auth_service = AuthService(db)

    try:
        user = await auth_service.register(
            username=request.username,
            email=request.email,
            password=request.password,
            phone=request.phone,
            tenant_id=request.tenant_id,
        )

        return {
            "message": "Registration submitted, pending approval",
            "user_id": user.id,
            "username": user.username,
        }
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.message),
        )


@router.post("/auth/switch-tenant", response_model=TokenResponse)
async def switch_tenant(
    request: SwitchTenantRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换当前租户"""
    auth_service = AuthService(db)

    try:
        access_token, refresh_token = await auth_service.switch_tenant(
            current_user.id,
            request.tenant_id
        )

        # 获取新的租户列表
        tenants = await auth_service.get_user_tenants(current_user.id)

        # 记录审计日志
        from apps.auth.services.auth import AuditService
        audit = AuditService(db)
        await audit.log(
            tenant_id=str(request.tenant_id),
            user_id=current_user.id,
            username=current_user.username,
            action="switch_tenant",
            resource_type="auth",
            ip_address=_get_client_ip(http_request),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60,
            user={
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "is_system": current_user.is_system,
            },
            tenants=tenants,
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


@router.get("/auth/tenants")
async def get_my_tenants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有租户"""
    auth_service = AuthService(db)
    tenants = await auth_service.get_user_tenants(current_user.id)
    return {"tenants": tenants}


@router.get("/auth/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户信息"""
    auth_service = AuthService(db)
    tenants = await auth_service.get_user_tenants(current_user.id)
    current_tenant = next((t for t in tenants if t["is_current"]), None)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_system": current_user.is_system,
        "current_tenant": current_tenant,
        "tenants": tenants,
    }


@router.get("/auth/permissions")
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户在当前租户的权限"""
    from apps.auth.dependencies import get_token_payload
    payload = get_token_payload()
    return {
        "tenant_id": payload.get("current_tenant_id") if payload else None,
        "is_system": payload.get("is_system", False) if payload else False,
        "is_superuser": payload.get("is_superuser", False) if payload else False,
        "permissions": payload.get("permissions", []) if payload else [],
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
    from apps.auth.dependencies import get_token_payload
    payload = get_token_payload()
    if not payload or not payload.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    api_key_auth = APIKeyAuth(db)
    api_key, full_api_key = await api_key_auth.create_api_key(
        tenant_id=payload.get("current_tenant_id"),
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
    from apps.auth.dependencies import get_token_payload
    payload = get_token_payload()
    api_key_auth = APIKeyAuth(db)
    keys = await api_key_auth.list_api_keys(payload.get("current_tenant_id") if payload else None)
    return {"api_keys": keys}


@router.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤销API Key"""
    from apps.auth.dependencies import get_token_payload
    payload = get_token_payload()
    if not payload or not payload.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    api_key_auth = APIKeyAuth(db)
    success = await api_key_auth.revoke_api_key(payload.get("current_tenant_id"), key_id)

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
