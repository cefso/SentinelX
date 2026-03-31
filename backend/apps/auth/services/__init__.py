"""
SentinelX - 租户服务
"""
from datetime import datetime
from typing import Optional, List
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.core.security import hash_password, verify_password, encryptor
from apps.core.exceptions import QuotaExceededError, DuplicateResourceError, ResourceNotFoundError
from apps.tenant.models import Tenant, User, Role, UserRole, Team
from apps.tenant.schemas import TenantCreate, TenantUpdate, UserCreate, UserUpdate

logger = structlog.get_logger(__name__)


class TenantService:
    """租户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(
        self,
        name: str,
        slug: str,
        admin_username: str,
        admin_email: str,
        admin_password: str,
        config: dict = None,
        max_alerts: int = 10000,
        max_users: int = 10,
        max_rules: int = 100,
        max_channels: int = 20,
        alert_qps: int = 100,
    ) -> Tenant:
        """创建租户及默认管理员"""
        # 检查slug唯一性
        existing = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError("Tenant", slug)

        # 创建租户
        tenant = Tenant(
            name=name,
            slug=slug,
            config=config or {},
            max_alerts=max_alerts,
            max_users=max_users,
            max_rules=max_rules,
            max_channels=max_channels,
            alert_qps=alert_qps,
        )
        self.db.add(tenant)
        await self.db.flush()

        # 创建管理员用户
        admin_user = User(
            tenant_id=tenant.id,
            username=admin_username,
            email=admin_email,
            password_hash=hash_password(admin_password),
            is_superuser=False,  # 租户管理员，不是系统超级管理员
        )
        self.db.add(admin_user)
        await self.db.flush()

        # 创建并分配默认角色
        admin_role = Role(
            tenant_id=tenant.id,
            name="管理员",
            code="admin",
            description="租户管理员",
            permissions=["*"],
            is_builtin=True,
        )
        viewer_role = Role(
            tenant_id=tenant.id,
            name="观察者",
            code="viewer",
            description="只读用户",
            permissions=["read"],
            is_builtin=True,
        )
        self.db.add(admin_role)
        self.db.add(viewer_role)
        await self.db.flush()

        # 分配管理员角色
        user_role = UserRole(
            user_id=admin_user.id,
            role_id=admin_role.id,
        )
        self.db.add(user_role)

        await self.db.commit()
        await self.db.refresh(tenant)

        logger.info("tenant_created", tenant_id=tenant.id, slug=slug)

        return tenant

    async def get_tenant(self, tenant_id: int) -> Optional[Tenant]:
        """获取租户"""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """获取租户列表"""
        result = await self.db.execute(
            select(Tenant)
            .where(Tenant.is_deleted == False)
            .order_by(Tenant.id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update_tenant(self, tenant_id: int, data: dict) -> Tenant:
        """更新租户"""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ResourceNotFoundError("Tenant", str(tenant_id))

        for key, value in data.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        await self.db.commit()
        await self.db.refresh(tenant)
        logger.info("tenant_updated", tenant_id=tenant_id)

        return tenant

    async def delete_tenant(self, tenant_id: int):
        """删除租户 (软删除)"""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ResourceNotFoundError("Tenant", str(tenant_id))

        tenant.is_deleted = True
        tenant.deleted_at = datetime.utcnow()
        await self.db.commit()
        logger.info("tenant_deleted", tenant_id=tenant_id)


class UserService:
    """用户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self,
        tenant_id: int,
        username: str,
        email: str,
        password: str,
        phone: str = None,
        role_ids: List[int] = None,
    ) -> User:
        """创建用户"""
        # 检查用户名唯一性
        existing = await self.db.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError("User", username)

        # 检查邮箱唯一性
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError("User", email)

        # 检查用户配额
        tenant_service = TenantService(self.db)
        tenant = await tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise ResourceNotFoundError("Tenant", str(tenant_id))

        user_count = await self.db.execute(
            select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.is_deleted == False
            )
        )
        count = user_count.scalar()
        if count >= tenant.max_users:
            raise QuotaExceededError("users", tenant.max_users)

        # 创建用户
        user = User(
            tenant_id=tenant_id,
            username=username,
            email=email,
            phone=phone,
            password_hash=hash_password(password),
        )
        self.db.add(user)
        await self.db.flush()

        # 分配角色
        if role_ids:
            for role_id in role_ids:
                user_role = UserRole(user_id=user.id, role_id=role_id)
                self.db.add(user_role)

        await self.db.commit()
        await self.db.refresh(user)

        logger.info("user_created", user_id=user.id, username=username, tenant_id=tenant_id)

        return user

    async def get_user(self, user_id: int, tenant_id: int = None) -> Optional[User]:
        """获取用户"""
        query = select(User).where(User.id == user_id)
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_users(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """获取用户列表"""
        result = await self.db.execute(
            select(User)
            .where(
                User.tenant_id == tenant_id,
                User.is_deleted == False
            )
            .order_by(User.id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update_user(self, user_id: int, tenant_id: int, data: dict) -> User:
        """更新用户"""
        user = await self.get_user(user_id, tenant_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))

        # 不允许通过此接口修改密码
        data.pop("password", None)
        data.pop("password_hash", None)

        for key, value in data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        logger.info("user_updated", user_id=user_id)

        return user

    async def change_password(self, user_id: int, old_password: str, new_password: str, tenant_id: int = None) -> bool:
        """修改密码"""
        user = await self.get_user(user_id, tenant_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))

        if not verify_password(old_password, user.password_hash):
            return False

        user.password_hash = hash_password(new_password)
        await self.db.commit()
        logger.info("password_changed", user_id=user_id)

        return True

    async def assign_roles(self, user_id: int, role_ids: List[int], tenant_id: int = None):
        """分配角色"""
        user = await self.get_user(user_id, tenant_id)
        if not user:
            raise ResourceNotFoundError("User", str(user_id))

        # 删除现有角色
        await self.db.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )

        # 添加新角色
        for role_id in role_ids:
            user_role = UserRole(user_id=user.id, role_id=role_id)
            self.db.add(user_role)

        await self.db.commit()
        logger.info("roles_assigned", user_id=user_id, role_ids=role_ids)


class RoleService:
    """角色服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_roles(self, user_id: int) -> List[Role]:
        """获取用户角色"""
        result = await self.db.execute(
            select(Role, UserRole.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return [role for role, _ in result.all()]

    async def create_role(
        self,
        tenant_id: int,
        name: str,
        code: str,
        permissions: List[str],
        description: str = None,
    ) -> Role:
        """创建角色"""
        role = Role(
            tenant_id=tenant_id,
            name=name,
            code=code,
            description=description,
            permissions=permissions,
        )
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)

        logger.info("role_created", role_id=role.id, name=name, tenant_id=tenant_id)

        return role
