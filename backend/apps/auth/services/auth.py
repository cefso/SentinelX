"""
SentinelX - 认证服务
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.core.exceptions import AuthenticationError, AuthorizationError
from apps.tenant.models import User, Role, UserRole
from apps.tenant.schemas import UserCreate

logger = structlog.get_logger(__name__)


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, username: str, password: str) -> Tuple[User, str, str]:
        """
        用户认证
        返回: (用户, access_token, refresh_token)
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning("auth_failed_user_not_found", username=username)
            raise AuthenticationError("Invalid username or password")

        if not verify_password(password, user.password_hash):
            logger.warning("auth_failed_wrong_password", username=username)
            raise AuthenticationError("Invalid username or password")

        if not user.is_active:
            logger.warning("auth_failed_inactive_user", username=username)
            raise AuthenticationError("User is inactive")

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await self.db.commit()

        # 生成令牌
        token_data = {
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info("auth_success", user_id=user.id, username=username)

        return user, access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """
        刷新令牌
        返回: (access_token, refresh_token)
        """
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise AuthenticationError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        token_data = {
            "sub": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
        }

        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        return new_access_token, new_refresh_token

    async def verify_access_token(self, token: str) -> Optional[dict]:
        """验证访问令牌"""
        return verify_token(token, "access")


class PermissionService:
    """权限服务"""

    # 内置权限定义
    PERMISSIONS = {
        # 告警权限
        "alert:read": "查看告警",
        "alert:write": "管理告警",
        "alert:delete": "删除告警",
        "alert:ack": "确认告警",

        # 规则权限
        "rule:read": "查看规则",
        "rule:write": "管理规则",
        "rule:delete": "删除规则",
        "rule:execute": "执行规则",

        # 渠道权限
        "channel:read": "查看渠道",
        "channel:write": "管理渠道",
        "channel:delete": "删除渠道",
        "channel:test": "测试渠道",

        # 用户权限
        "user:read": "查看用户",
        "user:write": "管理用户",
        "user:delete": "删除用户",

        # 租户权限
        "tenant:read": "查看租户",
        "tenant:write": "管理租户",
        "tenant:delete": "删除租户",

        # 系统权限
        "admin": "管理员(全部权限)",
        "read": "只读权限",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_permissions(self, user_id: int) -> list[str]:
        """获取用户的权限列表"""
        # 查询用户角色
        result = await self.db.execute(
            select(Role, UserRole.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        roles = result.all()

        permissions = set()
        for role, _ in roles:
            if role.permissions:
                if "*" in role.permissions:
                    # * 表示全部权限
                    return ["*"]
                permissions.update(role.permissions)

        return list(permissions)

    async def check_permission(self, user_id: int, permission: str) -> bool:
        """检查用户是否有指定权限"""
        permissions = await self.get_user_permissions(user_id)

        if "*" in permissions:
            return True

        return permission in permissions

    async def check_tenant_access(self, user_id: int, tenant_id: int, user: User) -> bool:
        """检查用户是否有访问指定租户的权限"""
        # 超级管理员可以访问所有租户
        if user.is_superuser:
            return True

        # 普通用户只能访问自己的租户
        return user.tenant_id == tenant_id

    def require_permission(self, permission: str):
        """权限检查装饰器工厂"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 从参数中获取user
                user = kwargs.get("current_user") or args[0] if args else None
                if not user:
                    raise AuthorizationError("User not found")

                if not self.check_permission(user.id, permission):
                    raise AuthorizationError(f"Permission denied: {permission}")

                return await func(*args, **kwargs)
            return wrapper
        return decorator


class AuditService:
    """审计日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        tenant_id: int,
        user_id: int,
        username: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        details: dict = None,
        ip_address: str = None,
    ):
        """记录审计日志"""
        from apps.tenant.models import AuditLog

        audit_log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        self.db.add(audit_log)
        await self.db.commit()

        logger.info(
            "audit_log",
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
        )
