"""
SentinelX - 初始数据种子脚本
应用启动时自动创建默认租户和超级管理员
"""
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import AsyncSessionLocal
from apps.core.security import hash_password
from apps.tenant.models import Tenant, User, Role, UserRole

logger = structlog.get_logger()

DEFAULT_TENANT_SLUG = "sentinelx"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@sentinelx.local"
DEFAULT_ADMIN_PASSWORD = "Admin@123456"


async def seed_default_data():
    """创建默认租户、角色和超级管理员"""
    async with AsyncSessionLocal() as session:
        try:
            # 检查是否已存在默认租户
            result = await session.execute(
                select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG)
            )
            existing_tenant = result.scalar_one_or_none()

            if existing_tenant:
                logger.info("default_tenant_exists", tenant_slug=DEFAULT_TENANT_SLUG)
                return

            logger.info("creating_default_tenant", slug=DEFAULT_TENANT_SLUG)

            # 创建默认租户
            tenant = Tenant(
                name="SentinelX Platform",
                slug=DEFAULT_TENANT_SLUG,
                config={"theme": "light", "timezone": "Asia/Shanghai"},
                max_alerts=100000,
                max_users=100,
                max_rules=500,
                max_channels=100,
                alert_qps=1000,
                is_active=True,
                is_deleted=False,
            )
            session.add(tenant)
            await session.flush()

            # 创建系统级角色
            system_roles = [
                Role(
                    tenant_id=None,
                    name="超级管理员",
                    code="superadmin",
                    description="系统级超级管理员，拥有所有权限",
                    permissions=["*"],
                    is_builtin=True,
                ),
                Role(
                    tenant_id=None,
                    name="管理员",
                    code="admin",
                    description="租户管理员，拥有租户内所有权限",
                    permissions=["*"],
                    is_builtin=True,
                ),
                Role(
                    tenant_id=None,
                    name="观察者",
                    code="viewer",
                    description="只读用户",
                    permissions=["read"],
                    is_builtin=True,
                ),
            ]
            for role in system_roles:
                session.add(role)
            await session.flush()

            # 创建租户级角色
            tenant_roles = [
                Role(
                    tenant_id=tenant.id,
                    name="租户管理员",
                    code="tenant_admin",
                    description="租户内管理员",
                    permissions=["*"],
                    is_builtin=False,
                ),
                Role(
                    tenant_id=tenant.id,
                    name="运维人员",
                    code="operator",
                    description="运维人员",
                    permissions=["read", "write", "alert:manage"],
                    is_builtin=False,
                ),
                Role(
                    tenant_id=tenant.id,
                    name="只读用户",
                    code="tenant_viewer",
                    description="租户只读用户",
                    permissions=["read"],
                    is_builtin=False,
                ),
            ]
            for role in tenant_roles:
                session.add(role)
            await session.flush()

            # 创建超级管理员用户
            admin_user = User(
                tenant_id=tenant.id,
                username=DEFAULT_ADMIN_USERNAME,
                email=DEFAULT_ADMIN_EMAIL,
                phone="+86-13800138000",
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                is_superuser=True,
                is_active=True,
                is_deleted=False,
            )
            session.add(admin_user)
            await session.flush()

            # 分配超级管理员角色
            result = await session.execute(
                select(Role).where(Role.code == "superadmin", Role.tenant_id.is_(None))
            )
            superadmin_role = result.scalar_one_or_none()

            if superadmin_role:
                user_role = UserRole(
                    user_id=admin_user.id,
                    role_id=superadmin_role.id,
                )
                session.add(user_role)

            await session.commit()
            logger.info(
                "default_data_created",
                tenant=DEFAULT_TENANT_SLUG,
                admin=DEFAULT_ADMIN_EMAIL,
            )
            logger.info("default_password", password=DEFAULT_ADMIN_PASSWORD)

        except Exception as e:
            logger.error("seed_data_error", error=str(e))
            await session.rollback()
            raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed_default_data())
