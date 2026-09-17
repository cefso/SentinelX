"""
SentinelX - 租户/认证安全修复回归测试
不依赖真实数据库，验证契约与关键鉴权逻辑。
"""
import inspect
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from apps.auth.schemas import APIKeyCreateRequest
from apps.tenant.schemas import TenantResponse
from apps.auth.services.auth import AuthService
from apps.core.exceptions import AuthenticationError
from apps.auth.api_key import APIKeyAuth


# ============ Schema 契约 ============

class TestTenantResponseNoSecrets:
    def test_response_has_no_api_token(self):
        fields = TenantResponse.model_fields
        assert "api_token" not in fields
        assert "webhook_api_key" not in fields


class TestAPIKeyCreateRequest:
    def test_body_model_fields(self):
        req = APIKeyCreateRequest(name="agent")
        assert req.name == "agent"
        assert req.expires_days is None

    def test_body_model_with_expiry(self):
        req = APIKeyCreateRequest(name="agent", expires_days=30)
        assert req.expires_days == 30

    def test_requires_name(self):
        with pytest.raises(Exception):
            APIKeyCreateRequest()


# ============ 路由依赖/权限门控 ============

class TestRouteSignatures:
    def test_list_users_requires_users_read(self):
        from apps.tenant.routers import list_users
        # current_user comes from require_permission("users:read")
        source = inspect.getsource(list_users)
        assert 'require_permission("users:read")' in source

    def test_list_tenants_scopes_non_system(self):
        from apps.tenant.routers import list_tenants
        source = inspect.getsource(list_tenants)
        assert "is_system" in source
        assert "UserTenant" in source

    def test_get_tenant_no_secret_fields_in_source(self):
        from apps.tenant.routers import get_tenant
        source = inspect.getsource(get_tenant)
        # 排除注释后的返回字典键
        assert '"api_token"' not in source
        assert "'api_token'" not in source
        assert '"webhook_api_key"' not in source
        assert "'webhook_api_key'" not in source
        assert "return {" in source
        assert '"webhook_url"' in source

    def test_webhook_key_requires_permission(self):
        from apps.tenant.routers import generate_webhook_key, get_webhook_key_info
        assert 'require_permission("tenants:write")' in inspect.getsource(generate_webhook_key)
        assert 'require_permission("tenants:read")' in inspect.getsource(get_webhook_key_info)

    def test_update_user_role_blocks_cross_tenant(self):
        from apps.tenant.routers import update_user_role
        source = inspect.getsource(update_user_role)
        assert "Cannot assign roles in another tenant" in source
        assert "is_system" in source

    def test_change_password_requires_old_password_for_self(self):
        from apps.tenant.routers import change_password
        source = inspect.getsource(change_password)
        assert "old_password is required" in source
        assert "users:write" in source

    def test_reset_permissions_scoped_to_current_tenant(self):
        from apps.tenant.routers import reset_user_permissions
        source = inspect.getsource(reset_user_permissions)
        assert "UserTenant.tenant_id == tenant_id" in source

    def test_api_key_routes_have_permission_deps(self):
        from apps.auth.routers import create_api_key, list_api_keys, revoke_api_key
        assert 'require_permission("api_keys:write")' in inspect.getsource(create_api_key)
        assert 'require_permission("api_keys:read")' in inspect.getsource(list_api_keys)
        assert 'require_permission("api_keys:delete")' in inspect.getsource(revoke_api_key)

    def test_create_api_key_uses_body_model(self):
        from apps.auth.routers import create_api_key
        sig = inspect.signature(create_api_key)
        params = sig.parameters
        assert "request" in params
        ann = str(params["request"].annotation)
        assert "APIKeyCreateRequest" in ann
        # 不再是裸 query 参数 name
        assert "name" not in params or params["name"].default is inspect.Parameter.empty


# ============ 运行时鉴权逻辑 ============

class TestUpdateUserRoleCrossTenant:
    @pytest.mark.asyncio
    async def test_non_system_cross_tenant_forbidden(self):
        from fastapi import HTTPException
        from apps.tenant.routers import update_user_role
        from apps.tenant.schemas import UserRoleUpdate, TenantRoleInput

        current = SimpleNamespace(id=1, is_system=False, is_superuser=False)
        request = UserRoleUpdate(
            tenant_roles=[TenantRoleInput(tenant_id=2, role_id=10)]
        )
        with pytest.raises(HTTPException) as exc:
            await update_user_role(
                user_id=99,
                request=request,
                tenant_id=1,
                db=MagicMock(),
                current_user=current,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_same_tenant_allowed(self):
        from apps.tenant.routers import update_user_role
        from apps.tenant.schemas import UserRoleUpdate, TenantRoleInput

        current = SimpleNamespace(id=1, is_system=False, is_superuser=False)
        request = UserRoleUpdate(
            tenant_roles=[TenantRoleInput(tenant_id=1, role_id=10)]
        )
        db = AsyncMock()
        # role lookup + user_tenant lookup
        db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: SimpleNamespace(id=10)),
            MagicMock(scalar_one_or_none=lambda: None),
        ])
        result = await update_user_role(
            user_id=99,
            request=request,
            tenant_id=1,
            db=db,
            current_user=current,
        )
        assert result["message"] == "Role updated successfully"


class TestChangePassword:
    @pytest.mark.asyncio
    async def test_self_change_requires_old_password(self):
        from fastapi import HTTPException
        from apps.tenant.routers import change_password
        from apps.tenant.schemas import UserPasswordUpdate

        current = SimpleNamespace(id=5, is_system=False)
        request = UserPasswordUpdate(new_password="newpass123")
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: SimpleNamespace(
            id=5, password_hash="hashed"
        )))
        with pytest.raises(HTTPException) as exc:
            await change_password(
                user_id=5,
                request=request,
                tenant_id=1,
                db=db,
                current_user=current,
            )
        assert exc.value.status_code == 400
        assert "old_password" in exc.value.detail

    @pytest.mark.asyncio
    async def test_other_user_requires_users_write(self):
        from fastapi import HTTPException
        from apps.tenant.routers import change_password
        from apps.tenant.schemas import UserPasswordUpdate

        current = SimpleNamespace(id=1, is_system=False)
        request = UserPasswordUpdate(new_password="newpass123")
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: SimpleNamespace(
            id=5, password_hash="hashed"
        )))
        with patch("apps.tenant.routers.get_token_payload", return_value={"permissions": ["alerts:read"]}):
            with pytest.raises(HTTPException) as exc:
                await change_password(
                    user_id=5,
                    request=request,
                    tenant_id=1,
                    db=db,
                    current_user=current,
                )
        assert exc.value.status_code == 403


class TestWebhookKeyScope:
    @pytest.mark.asyncio
    async def test_cross_tenant_webhook_key_forbidden(self):
        from fastapi import HTTPException
        from apps.tenant.routers import generate_webhook_key

        current = SimpleNamespace(id=1, is_system=False)
        with pytest.raises(HTTPException) as exc:
            await generate_webhook_key(
                tenant_id=2,
                db=AsyncMock(),
                current_user=current,
                current_tenant_id=1,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_system_can_generate_any_tenant_key(self):
        from apps.tenant.routers import generate_webhook_key

        current = SimpleNamespace(id=1, is_system=True)
        db = AsyncMock()
        tenant = SimpleNamespace(id=2, slug="t2", webhook_api_key=None)
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: tenant))
        db.commit = AsyncMock()
        result = await generate_webhook_key(
            tenant_id=2,
            db=db,
            current_user=current,
            current_tenant_id=1,
        )
        assert "api_key" in result
        assert result["api_key"].startswith("wh_")
        assert tenant.webhook_api_key is not None


class TestRequireTenantMember:
    @pytest.mark.asyncio
    async def test_member_allowed(self):
        from apps.tenant.routers import _require_tenant_member

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: 1))
        current = SimpleNamespace(id=1, is_system=False, is_superuser=False)
        await _require_tenant_member(db, current, tenant_id=1)  # no raise

    @pytest.mark.asyncio
    async def test_non_member_forbidden(self):
        from fastapi import HTTPException
        from apps.tenant.routers import _require_tenant_member

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        current = SimpleNamespace(id=1, is_system=False, is_superuser=False)
        with pytest.raises(HTTPException) as exc:
            await _require_tenant_member(db, current, tenant_id=2)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_system_bypasses_membership(self):
        from apps.tenant.routers import _require_tenant_member

        db = AsyncMock()
        current = SimpleNamespace(id=1, is_system=True, is_superuser=False)
        await _require_tenant_member(db, current, tenant_id=999)  # no raise
        db.execute.assert_not_called()


# ============ Refresh is_approved ============

class TestRefreshChecksApproval:
    @pytest.mark.asyncio
    async def test_unapproved_user_cannot_refresh(self):
        db = AsyncMock()
        user = SimpleNamespace(
            id=1, username="u", is_active=True, is_approved=False, is_system=False
        )
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: user))

        auth = AuthService(db)
        token = "dummy"
        with patch("apps.auth.services.auth.verify_token", return_value={"user_id": 1}):
            with pytest.raises(AuthenticationError) as exc:
                await auth.refresh_tokens(token)
        assert "approval" in str(exc.value.message).lower() or "pending" in str(exc.value.message).lower()

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_refresh(self):
        db = AsyncMock()
        user = SimpleNamespace(
            id=1, username="u", is_active=False, is_approved=True, is_system=False
        )
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: user))

        auth = AuthService(db)
        with patch("apps.auth.services.auth.verify_token", return_value={"user_id": 1}):
            with pytest.raises(AuthenticationError):
                await auth.refresh_tokens("dummy")


# ============ API Key legacy inactive key ============

class TestAPIKeyLegacyInactive:
    @pytest.mark.asyncio
    async def test_inactive_key_continues_scan(self):
        import json

        tenant_a = SimpleNamespace(
            id=1,
            slug="a",
            is_active=True,
            api_token=json.dumps({
                "kid1": {
                    "is_active": False,
                    "secret_signature": "sig",
                    "expires_at": None,
                }
            }),
        )
        tenant_b = SimpleNamespace(
            id=2,
            slug="b",
            is_active=True,
            api_token=json.dumps({
                "kid1": {
                    "is_active": True,
                    "secret_signature": "sig",
                    "expires_at": None,
                }
            }),
        )

        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [tenant_a, tenant_b])))

        api_key_auth = APIKeyAuth(db)
        with patch.object(api_key_auth, "_calculate_signature", return_value="sig"):
            result = await api_key_auth._verify_legacy("sxk_v1_kid1_secret", "kid1", "secret")

        assert result is tenant_b
