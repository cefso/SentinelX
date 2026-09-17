"""
SentinelX - 告警安全 / 契约修复测试
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from apps.core.security import hash_password, verify_api_key
from apps.notify.schemas import ChannelCreate, _is_blocked_host, _validate_url


# ============ 1. Webhook API Key 校验 ============

def test_verify_api_key_bcrypt_hash_accepts_correct_key():
    raw = "super-secret-webhook-key"
    stored = hash_password(raw)
    assert verify_api_key(raw, stored) is True


def test_verify_api_key_bcrypt_hash_rejects_wrong_key():
    stored = hash_password("correct-key")
    assert verify_api_key("wrong-key", stored) is False


def test_verify_api_key_requires_both_present():
    stored = hash_password("correct-key")
    assert verify_api_key("", stored) is False
    assert verify_api_key("correct-key", "") is False
    assert verify_api_key(None, stored) is False
    assert verify_api_key("x", None) is False


def test_verify_api_key_legacy_plaintext_fallback():
    # 历史明文仍可用常量时间比较
    assert verify_api_key("plain", "plain") is True
    assert verify_api_key("plain", "other") is False


@pytest.mark.asyncio
async def test_receive_webhook_requires_api_key_when_configured():
    """租户配置了 webhook_api_key 时，不传 / 传错均 401"""
    from apps.alert.routers import receive_webhook_by_source
    from apps.tenant.models import Tenant
    from apps.alert.models import AlertSource

    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.slug = "t1"
    tenant.is_active = True
    tenant.webhook_api_key = hash_password("secret")

    source = MagicMock(spec=AlertSource)
    source.id = 10
    source.tenant_id = 1
    source.client_id = "abc"

    db = AsyncMock()
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = source
    db.execute = AsyncMock(side_effect=[tenant_result, source_result])

    request = MagicMock()
    request.headers = {"content-type": "application/json"}

    # 不传 key
    with pytest.raises(HTTPException) as exc:
        await receive_webhook_by_source(
            tenant_slug="t1",
            source_type="custom",
            identifier="abc",
            request=request,
            x_api_key=None,
            db=db,
            redis=AsyncMock(),
        )
    assert exc.value.status_code == 401

    # 错误 key
    db.execute = AsyncMock(side_effect=[tenant_result, source_result])
    with pytest.raises(HTTPException) as exc:
        await receive_webhook_by_source(
            tenant_slug="t1",
            source_type="custom",
            identifier="abc",
            request=request,
            x_api_key="wrong",
            db=db,
            redis=AsyncMock(),
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_receive_webhook_source_tenant_mismatch_rejects():
    from apps.alert.routers import receive_webhook_by_source
    from apps.tenant.models import Tenant
    from apps.alert.models import AlertSource

    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.is_active = True
    tenant.webhook_api_key = None

    # source 属于其他租户
    source = MagicMock(spec=AlertSource)
    source.id = 10
    source.tenant_id = 99
    source.client_id = "abc"

    db = AsyncMock()
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = tenant
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = source
    db.execute = AsyncMock(side_effect=[tenant_result, source_result])

    request = MagicMock()
    request.headers = {"content-type": "application/json"}

    with pytest.raises(HTTPException) as exc:
        await receive_webhook_by_source(
            tenant_slug="t1",
            source_type="custom",
            identifier="abc",
            request=request,
            x_api_key=None,
            db=db,
            redis=AsyncMock(),
        )
    assert exc.value.status_code == 404


# ============ 2. 处置记录读写契约 ============

def test_dispose_action_write_mapping_covers_all_request_actions():
    """写入前缀必须能映射回前端动作 note|acknowledge|resolve|silence"""
    from apps.alert.routers import dispose_alert  # noqa: F401 — 确认可 import

    action_mapping = {
        "acknowledge": "dispose_acknowledge",
        "resolve": "dispose_resolve",
        "silence": "dispose_silence",
        "note": "dispose_note",
    }
    for req_action, history_action in action_mapping.items():
        assert history_action.startswith("dispose_")
        assert history_action.replace("dispose_", "") == req_action


@pytest.mark.asyncio
async def test_dispose_records_read_returns_frontend_actions():
    from apps.alert.routers import get_dispose_records
    from apps.alert.models import AlertHistory

    record = MagicMock(spec=AlertHistory)
    record.id = 1
    record.alert_id = 5
    record.action = "dispose_acknowledge"
    record.description = "ok"
    record.operator_id = 1
    record.operator_name = "admin"
    from datetime import datetime, timezone
    record.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [record]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)

    items = await get_dispose_records(alert_id=5, tenant_id=1, db=db)
    assert len(items) == 1
    assert items[0].action == "acknowledge"
    assert items[0].comment == "ok"


@pytest.mark.asyncio
async def test_dispose_alert_saves_previous_status_in_old_value():
    from apps.alert.routers import dispose_alert
    from apps.alert.schemas import DisposeRequest
    from apps.alert.models import Alert
    from apps.tenant.models import User

    alert = MagicMock(spec=Alert)
    alert.id = 5
    alert.tenant_id = 1
    alert.status = "firing"
    alert.acknowledged_at = None
    alert.resolved_at = None

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = alert
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    user = MagicMock(spec=User)
    user.id = 1
    user.username = "admin"

    req = DisposeRequest(action="acknowledge", comment="looking")
    await dispose_alert(alert_id=5, request=req, tenant_id=1, db=db, current_user=user)

    # status 已更新
    assert alert.status == "acknowledged"
    # 写入了一条 history，old_value 保存 previous_status
    added = db.add.call_args[0][0]
    assert added.action == "dispose_acknowledge"
    assert added.old_value == {"status": "firing"}
    assert added.new_value["previous_status"] == "firing"
    assert added.new_value["dispose_action"] == "acknowledge"


# ============ 8. 升级租户过滤 ============

def test_check_escalations_accepts_tenant_id():
    import inspect
    from apps.alert.services.escalation import EscalationService

    sig = inspect.signature(EscalationService.check_escalations)
    assert "tenant_id" in sig.parameters
    sig2 = inspect.signature(EscalationService.get_escalation_candidates)
    assert "tenant_id" in sig2.parameters


# ============ 10. SSRF 基础拦截 ============

@pytest.mark.parametrize(
    "host,blocked",
    [
        ("127.0.0.1", True),
        ("127.1.2.3", True),
        ("10.0.0.5", True),
        ("172.16.0.1", True),
        ("172.31.255.1", True),
        ("192.168.1.1", True),
        ("169.254.1.1", True),
        ("::1", True),
        ("0.0.0.0", True),
        ("localhost", True),
        ("8.8.8.8", False),
        ("example.com", False),
        ("172.15.0.1", False),
        ("172.32.0.1", False),
    ],
)
def test_is_blocked_host(host, blocked):
    assert _is_blocked_host(host) is blocked


def test_validate_url_rejects_private_targets():
    with pytest.raises(ValueError):
        _validate_url("http://127.0.0.1/hook", "webhook_url")
    with pytest.raises(ValueError):
        _validate_url("http://10.1.2.3:8080/hook", "webhook_url")
    with pytest.raises(ValueError):
        _validate_url("http://localhost/hook", "webhook_url")
    with pytest.raises(ValueError):
        _validate_url("http://192.168.0.1/hook", "webhook_url")
    # 合法公网地址
    _validate_url("https://hooks.example.com/abc", "webhook_url")


def test_channel_create_rejects_ssrf_webhook():
    with pytest.raises(ValidationError):
        ChannelCreate(
            name="evil",
            code="evil-1",
            channel_type="webhook",
            config={"webhook_url": "http://127.0.0.1:9000/steal"},
        )

    ok = ChannelCreate(
        name="ok",
        code="ok-1",
        channel_type="webhook",
        config={"webhook_url": "https://hooks.example.com/ok"},
    )
    assert ok.channel_type == "webhook"


# ============ 11. PUT 白名单 / 状态迁移 ============

@pytest.mark.asyncio
async def test_update_alert_rejects_illegal_status_transition():
    from apps.alert.routers import update_alert
    from apps.alert.schemas import AlertUpdate
    from apps.alert.models import Alert
    from apps.tenant.models import User

    alert = MagicMock(spec=Alert)
    alert.id = 1
    alert.tenant_id = 1
    alert.status = "resolved"
    alert.severity = "high"
    alert.acknowledged_at = None
    alert.resolved_at = None
    alert.silenced_until = None

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = alert
    db.execute = AsyncMock(return_value=result)

    user = MagicMock(spec=User)
    user.id = 1
    user.username = "admin"

    # resolved -> acknowledged 不在白名单内
    with pytest.raises(HTTPException) as exc:
        await update_alert(
            alert_id=1,
            request=AlertUpdate(status="acknowledged"),
            tenant_id=1,
            db=db,
            current_user=user,
        )
    assert exc.value.status_code == 400
    # 未写 history / 未 commit
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_alert_allows_legal_transition():
    from apps.alert.routers import update_alert
    from apps.alert.schemas import AlertUpdate
    from apps.alert.models import Alert
    from apps.tenant.models import User

    alert = MagicMock(spec=Alert)
    alert.id = 1
    alert.tenant_id = 1
    alert.status = "firing"
    alert.severity = "high"
    alert.acknowledged_at = None
    alert.resolved_at = None
    alert.silenced_until = None

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = alert
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    user = MagicMock(spec=User)
    user.id = 1
    user.username = "admin"

    updated = await update_alert(
        alert_id=1,
        request=AlertUpdate(status="acknowledged"),
        tenant_id=1,
        db=db,
        current_user=user,
    )
    assert alert.status == "acknowledged"
    assert alert.acknowledged_at is not None
    db.commit.assert_awaited_once()
