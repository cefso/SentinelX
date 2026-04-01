"""
SentinelX - 认证服务
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from apps.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.core.exceptions import AuthenticationError, AuthorizationError
from apps.tenant.models import User, Role, UserTenant, Tenant

logger = structlog.get_logger(__name__)


class AuthService:
    """认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, username: str, password: str) -> Tuple[User, str, str, List[Dict[str, Any]]]:
        """
        用户认证
        返回: (用户, access_token, refresh_token, 租户列表)
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

        if not user.is_approved:
            logger.warning("auth_failed_not_approved", username=username)
            raise AuthenticationError("Registration pending approval")

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()

        # 获取用户的租户列表
        tenants = await self.get_user_tenants(user.id)

        # 如果用户没有任何租户关联且不是系统管理员，抛出异常
        if not tenants:
            if user.is_system:
                # 系统管理员可以没有租户关联
                tenants = []
            else:
                logger.warning("auth_failed_no_tenants", user_id=user.id, username=username)
                raise AuthenticationError("User has no tenant associations")

        # 确保有一个当前租户（系统管理员可以没有）
        if tenants:
            current_tenant = next((t for t in tenants if t["is_current"]), tenants[0])
            if not any(t["is_current"] for t in tenants):
                # 将第一个租户设为当前租户
                current_tenant = tenants[0]
                await self._set_current_tenant(user.id, current_tenant["id"])
            current_tenant_id = current_tenant["id"]
            is_superuser = current_tenant.get("is_superuser", False)
            permissions = current_tenant.get("permissions", [])
        else:
            current_tenant = None
            current_tenant_id = None
            is_superuser = True  # 系统管理员拥有全部权限
            permissions = ["*"]

        await self.db.commit()

        # 生成令牌
        token_data = {
            "sub": str(user.id),
            "user_id": user.id,
            "username": user.username,
            "current_tenant_id": current_tenant_id,
            "is_system": user.is_system,
            "is_superuser": is_superuser,
            "permissions": permissions,
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info("auth_success", user_id=user.id, username=username, current_tenant_id=current_tenant_id)

        return user, access_token, refresh_token, tenants

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        phone: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> User:
        """
        用户注册
        创建用户后 is_approved=False，需要管理员审批
        如果指定了 tenant_id，同时创建 UserTenant 关联
        """
        # 检查用户名唯一性
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            raise AuthenticationError("Username already exists")

        # 检查邮箱唯一性
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        if result.scalar_one_or_none():
            raise AuthenticationError("Email already exists")

        # 创建用户
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            phone=phone,
            is_system=False,
            is_superuser=False,
            is_active=False,  # 注册用户默认未激活
            is_approved=False,  # 注册用户默认未审批
        )
        self.db.add(user)
        await self.db.flush()

        # 如果指定了租户，创建关联（但不激活，等审批通过后激活）
        if tenant_id:
            # 验证租户存在且活跃
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active == True)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                raise AuthenticationError("Tenant not found or inactive")

            # 获取 viewer 角色（默认普通用户角色）
            result = await self.db.execute(
                select(Role).where(Role.tenant_id == tenant_id, Role.code == "viewer")
            )
            viewer_role = result.scalar_one_or_none()
            if not viewer_role:
                # 如果没有 viewer 角色，获取该租户第一个角色
                result = await self.db.execute(
                    select(Role).where(Role.tenant_id == tenant_id).order_by(Role.id)
                )
                viewer_role = result.scalar_one_or_none()

            if viewer_role:
                user_tenant = UserTenant(
                    user_id=user.id,
                    tenant_id=tenant_id,
                    role_id=viewer_role.id,
                    is_current=False,
                    is_primary=True,
                )
                self.db.add(user_tenant)

        await self.db.commit()
        await self.db.refresh(user)

        logger.info("user_registered", user_id=user.id, username=username, tenant_id=tenant_id)

        return user

    async def get_user_tenants(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有租户关联"""
        result = await self.db.execute(
            select(UserTenant, Role, Tenant)
            .join(Role, Role.id == UserTenant.role_id)
            .join(Tenant, Tenant.id == UserTenant.tenant_id)
            .where(UserTenant.user_id == user_id)
            .where(Tenant.is_active == True)
        )
        rows = result.all()

        tenants = []
        for ut, role, tenant in rows:
            tenants.append({
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant.slug,
                "role": {
                    "id": role.id,
                    "code": role.code,
                    "name": role.name,
                },
                "is_current": ut.is_current,
                "is_superuser": role.code in ("admin", "system_admin") or role.permissions == ["*"],
                "permissions": role.permissions or [],
            })

        return tenants

    async def _set_current_tenant(self, user_id: int, tenant_id: int):
        """设置当前租户"""
        # 取消所有当前标记
        await self.db.execute(
            select(UserTenant)
            .where(UserTenant.user_id == user_id)
        )
        result = await self.db.execute(
            select(UserTenant)
            .where(UserTenant.user_id == user_id)
        )
        user_tenants = result.scalars().all()
        for ut in user_tenants:
            ut.is_current = (ut.tenant_id == tenant_id)
        await self.db.commit()

    async def switch_tenant(self, user_id: int, new_tenant_id: int) -> Tuple[str, str]:
        """切换用户当前租户"""
        # 验证用户是否属于该租户
        result = await self.db.execute(
            select(UserTenant, Tenant)
            .join(Tenant, Tenant.id == UserTenant.tenant_id)
            .where(UserTenant.user_id == user_id)
            .where(UserTenant.tenant_id == new_tenant_id)
        )
        row = result.one_or_none()

        if not row:
            raise AuthenticationError("User does not belong to this tenant")

        user_tenant, tenant = row
        if not tenant.is_active:
            raise AuthenticationError("Tenant is inactive")

        # 更新当前租户标记
        await self._set_current_tenant(user_id, new_tenant_id)

        # 获取新租户信息并生成新token
        tenants = await self.get_user_tenants(user_id)
        current_tenant = next((t for t in tenants if t["id"] == new_tenant_id), tenants[0])

        user = await self.db.get(User, user_id)

        token_data = {
            "sub": str(user.id),
            "user_id": user.id,
            "username": user.username,
            "current_tenant_id": current_tenant["id"],
            "is_system": user.is_system,
            "is_superuser": current_tenant.get("is_superuser", False),
            "permissions": current_tenant.get("permissions", []),
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        logger.info("tenant_switched", user_id=user_id, new_tenant_id=new_tenant_id)

        return access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """
        刷新令牌
        返回: (access_token, refresh_token)
        """
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise AuthenticationError("Invalid or expired refresh token")

        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationError("Invalid token payload")

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise AuthenticationError("Invalid token payload")

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # 获取当前租户信息
        tenants = await self.get_user_tenants(user_id)
        current_tenant = next((t for t in tenants if t["is_current"]), tenants[0] if tenants else None)

        if not current_tenant:
            raise AuthenticationError("User has no active tenant")

        token_data = {
            "sub": str(user.id),
            "user_id": user.id,
            "username": user.username,
            "current_tenant_id": current_tenant["id"],
            "is_system": user.is_system,
            "is_superuser": current_tenant.get("is_superuser", False),
            "permissions": current_tenant.get("permissions", []),
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
        "alerts:read": "查看告警",
        "alerts:write": "管理告警",
        "alerts:delete": "删除告警",
        "alerts:ack": "确认告警",

        # 规则权限
        "rules:read": "查看规则",
        "rules:write": "管理规则",
        "rules:delete": "删除规则",
        "rules:execute": "执行规则",

        # 渠道权限
        "channels:read": "查看渠道",
        "channels:write": "管理渠道",
        "channels:delete": "删除渠道",
        "channels:test": "测试渠道",

        # 用户权限
        "users:read": "查看用户",
        "users:write": "管理用户",
        "users:delete": "删除用户",

        # 租户权限
        "tenants:read": "查看租户",
        "tenants:write": "管理租户",
        "tenants:delete": "删除租户",

        # 系统权限
        "admin": "管理员(全部权限)",
        "read": "只读权限",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_role_permissions(self, role_id: int) -> list[str]:
        """获取角色的权限列表"""
        role = await self.db.get(Role, role_id)
        if not role:
            return []
        return role.permissions or []

    def check_permission(self, permissions: list[str], required_permission: str) -> bool:
        """检查是否有指定权限"""
        if "*" in permissions:
            return True
        return required_permission in permissions

    def check_tenant_access(self, is_system: bool, is_superuser: bool, current_tenant_id: int, target_tenant_id: int) -> bool:
        """检查是否有访问目标租户的权限"""
        # 系统管理员可以访问所有租户
        if is_system:
            return True
        # 租户管理员可以访问同租户
        if is_superuser and current_tenant_id == target_tenant_id:
            return True
        # 普通用户只能访问自己的租户
        return current_tenant_id == target_tenant_id


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
            tenant_id=str(tenant_id),
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
