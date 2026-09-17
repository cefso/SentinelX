"""
JWT 权限/超级用户陈旧快照修复回归测试

验证: require_permission / require_superuser 以 DB 为权威来源，
      不再信任 JWT claim 中的 permissions / is_superuser / is_system。
不依赖真实数据库。
"""
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from apps.auth.dependencies import require_permission, require_superuser, set_token_payload
from apps.auth.services.auth import PermissionService


# ============ PermissionService.get_user_tenant_authz ============

class TestGetUserTenantAuthz:
    async def test_is_system_grants_all(self):
        svc = PermissionService(db=AsyncMock())
        ctx = await svc.get_user_tenant_authz(user_id=1, tenant_id=1, is_system=True)
        assert ctx["permissions"] == ["*"]
        assert ctx["is_superuser"] is True

    async def test_no_tenant_non_system_denied(self):
        svc = PermissionService(db=AsyncMock())
        ctx = await svc.get_user_tenant_authz(user_id=1, tenant_id=None, is_system=False)
        assert ctx["permissions"] == []
        assert ctx["is_superuser"] is False

    async def test_no_membership_returns_empty(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: None))
        svc = PermissionService(db=db)
        ctx = await svc.get_user_tenant_authz(user_id=1, tenant_id=9, is_system=False)
        assert ctx["permissions"] == []
        assert ctx["is_superuser"] is False

    async def test_loads_role_permissions_from_db(self):
        role = SimpleNamespace(code="viewer", permissions=["alerts:read", "rules:read"])
        ut = SimpleNamespace(user_id=1, tenant_id=1, role_id=10)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: (ut, role)))
        svc = PermissionService(db=db)

        ctx = await svc.get_user_tenant_authz(user_id=1, tenant_id=1, is_system=False)
        assert ctx["permissions"] == ["alerts:read", "rules:read"]
        assert ctx["is_superuser"] is False

    async def test_admin_role_is_superuser(self):
        role = SimpleNamespace(code="admin", permissions=["*"])
        ut = SimpleNamespace(user_id=1, tenant_id=1, role_id=2)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: (ut, role)))
        svc = PermissionService(db=db)

        ctx = await svc.get_user_tenant_authz(user_id=1, tenant_id=1, is_system=False)
        assert ctx["is_superuser"] is True
        assert ctx["permissions"] == ["*"]

    async def test_system_admin_role_code_is_superuser(self):
        role = SimpleNamespace(code="system_admin", permissions=["users:read"])
        ut = SimpleNamespace(user_id=1, tenant_id=1, role_id=3)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: (ut, role)))
        svc = PermissionService(db=db)

        ctx = await svc.get_user_tenant_authz(user_id=1, tenant_id=1, is_system=False)
        assert ctx["is_superuser"] is True


class TestMatchPermission:
    def test_wildcard_star(self):
        svc = PermissionService(db=None)
        assert svc.match_permission(["*"], "alerts:delete") is True

    def test_wildcard_admin(self):
        svc = PermissionService(db=None)
        assert svc.match_permission(["admin"], "tenants:write") is True

    def test_read_meta_matches_suffix(self):
        svc = PermissionService(db=None)
        assert svc.match_permission(["alerts:read"], "read") is True
        assert svc.match_permission(["read"], "read") is True
        assert svc.match_permission(["alerts:write"], "read") is False

    def test_exact_match(self):
        svc = PermissionService(db=None)
        assert svc.match_permission(["alerts:write"], "alerts:write") is True
        assert svc.match_permission(["alerts:read"], "alerts:write") is False

    def test_empty_denied(self):
        svc = PermissionService(db=None)
        assert svc.match_permission([], "alerts:read") is False


# ============ require_permission: DB 优先于 claim ============

class TestRequirePermissionDBFresh:
    async def test_db_denies_even_when_claim_grants(self):
        """JWT claim 含 alerts:write，但 DB 角色只有 alerts:read → 必须拒绝"""
        user = SimpleNamespace(id=42, is_system=False, is_active=True)
        db = AsyncMock()

        set_token_payload({
            "user_id": 42,
            "current_tenant_id": 1,
            "permissions": ["alerts:write", "*"],  # 陈旧 claim
            "is_superuser": True,
        })

        role = SimpleNamespace(code="viewer", permissions=["alerts:read"])
        ut = SimpleNamespace(user_id=42, tenant_id=1, role_id=10)
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: (ut, role)))

        check = require_permission("alerts:write")
        with pytest.raises(HTTPException) as exc:
            await check(current_user=user, db=db)
        assert exc.value.status_code == 403
        assert "alerts:write" in exc.value.detail

    async def test_db_grants_even_when_claim_denies(self):
        """JWT claim 无权限，但 DB 角色有 → 必须放行"""
        user = SimpleNamespace(id=42, is_system=False, is_active=True)
        db = AsyncMock()

        set_token_payload({
            "user_id": 42,
            "current_tenant_id": 1,
            "permissions": [],  # 陈旧 claim
            "is_superuser": False,
        })

        role = SimpleNamespace(code="operator", permissions=["alerts:write"])
        ut = SimpleNamespace(user_id=42, tenant_id=1, role_id=11)
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: (ut, role)))

        check = require_permission("alerts:write")
        result = await check(current_user=user, db=db)
        assert result is user

    async def test_is_system_from_db_user_grants(self):
        """User.is_system=True（DB 字段）时全量放行，不查角色"""
        user = SimpleNamespace(id=7, is_system=True, is_active=True)
        db = AsyncMock()
        # 不应触发角色查询；若触发则 execute 未配置会失败
        db.execute = AsyncMock(side_effect=AssertionError("should not query role for is_system"))

        set_token_payload({
            "user_id": 7,
            "current_tenant_id": 1,
            "permissions": [],  # claim 无权限
        })

        check = require_permission("tenants:delete")
        result = await check(current_user=user, db=db)
        assert result is user

    async def test_membership_removed_denies(self):
        """用户已被移出租户（无 UserTenant 行）→ 即使 claim 有 * 也拒绝"""
        user = SimpleNamespace(id=42, is_system=False, is_active=True)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: None))

        set_token_payload({
            "user_id": 42,
            "current_tenant_id": 1,
            "permissions": ["*"],
            "is_superuser": True,
        })

        check = require_permission("alerts:read")
        with pytest.raises(HTTPException) as exc:
            await check(current_user=user, db=db)
        assert exc.value.status_code == 403

    async def test_api_key_virtual_user_bypasses_db(self):
        """API Key 虚拟用户 (id=0) 保持全量权限，不查 DB 角色"""
        user = SimpleNamespace(id=0, is_system=False, is_active=True)
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=AssertionError("api key should not hit role DB"))

        set_token_payload({
            "user_id": 0,
            "current_tenant_id": 1,
            "permissions": ["*"],
            "is_superuser": True,
        })

        check = require_permission("alerts:delete")
        result = await check(current_user=user, db=db)
        assert result is user


# ============ require_superuser: 以 DB 为准 ============

class TestRequireSuperuserDBFresh:
    async def test_revoked_is_system_denies(self):
        """claim 说 is_system=True，但 DB User.is_system=False → 必须拒绝"""
        user = SimpleNamespace(id=5, is_system=False, is_active=True)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: None))  # 无租户 admin 角色

        set_token_payload({
            "user_id": 5,
            "current_tenant_id": 1,
            "is_system": True,       # 陈旧 claim
            "is_superuser": True,    # 陈旧 claim
        })

        check = require_superuser()
        with pytest.raises(HTTPException) as exc:
            await check(current_user=user, db=db)
        assert exc.value.status_code == 403

    async def test_db_is_system_grants(self):
        """DB User.is_system=True → 放行，即使 claim 已被改掉"""
        user = SimpleNamespace(id=5, is_system=True, is_active=True)
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=AssertionError("is_system should short-circuit"))

        set_token_payload({
            "user_id": 5,
            "current_tenant_id": 1,
            "is_system": False,
            "is_superuser": False,
        })

        check = require_superuser()
        result = await check(current_user=user, db=db)
        assert result is user

    async def test_claim_superuser_but_db_role_not_admin_denies(self):
        """claim is_superuser=True，但 DB 角色是 viewer → 必须拒绝"""
        user = SimpleNamespace(id=9, is_system=False, is_active=True)
        db = AsyncMock()

        role = SimpleNamespace(code="viewer", permissions=["alerts:read"])
        ut = SimpleNamespace(user_id=9, tenant_id=2, role_id=20)
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: (ut, role)))

        set_token_payload({
            "user_id": 9,
            "current_tenant_id": 2,
            "is_superuser": True,  # 陈旧 claim
        })

        check = require_superuser()
        with pytest.raises(HTTPException) as exc:
            await check(current_user=user, db=db)
        assert exc.value.status_code == 403

    async def test_db_admin_role_grants_even_if_claim_false(self):
        """claim is_superuser=False，但 DB 角色是 admin → 放行"""
        user = SimpleNamespace(id=9, is_system=False, is_active=True)
        db = AsyncMock()

        role = SimpleNamespace(code="admin", permissions=["*"])
        ut = SimpleNamespace(user_id=9, tenant_id=2, role_id=2)
        db.execute = AsyncMock(return_value=MagicMock(first=lambda: (ut, role)))

        set_token_payload({
            "user_id": 9,
            "current_tenant_id": 2,
            "is_superuser": False,  # 陈旧 claim
        })

        check = require_superuser()
        result = await check(current_user=user, db=db)
        assert result is user

    async def test_api_key_virtual_superuser_allowed(self):
        user = SimpleNamespace(id=0, is_system=False, is_active=True)
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=AssertionError("api key should not hit role DB"))

        set_token_payload({
            "user_id": 0,
            "current_tenant_id": 1,
            "is_superuser": True,
        })

        check = require_superuser()
        result = await check(current_user=user, db=db)
        assert result is user
