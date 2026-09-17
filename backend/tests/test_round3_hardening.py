"""第三轮审计硬化：SSRF 发送时校验、regex ReDoS、stats 缓存、云指标 system 边界"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.notify.schemas import validate_outbound_url
from apps.rule.engine import _safe_regex_match


# ============ SSRF 发送时校验 ============

def test_validate_outbound_url_blocks_private():
    with pytest.raises(ValueError):
        validate_outbound_url("http://127.0.0.1:6379/")
    with pytest.raises(ValueError):
        validate_outbound_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(ValueError):
        validate_outbound_url("http://10.0.0.1/hook")
    with pytest.raises(ValueError):
        validate_outbound_url("http://192.168.1.1/x")


def test_validate_outbound_url_allows_public():
    validate_outbound_url("https://hooks.example.com/path")


@pytest.mark.asyncio
async def test_webhook_channel_rejects_private_url_at_send():
    from apps.notify.channels.webhook import WebhookChannel

    ch = WebhookChannel({"webhook_url": "http://127.0.0.1/hook"})
    alert = MagicMock()
    alert.id = 1
    ok, err = await ch.send(alert)
    assert ok is False
    assert err and "内网" in err or "本机" in err or "URL" in err


# ============ regex ReDoS ============

def test_safe_regex_match_basic():
    assert _safe_regex_match(r"^prod-", "prod-web-01") is True
    assert _safe_regex_match(r"^prod-", "staging-web") is False


def test_safe_regex_match_rejects_nested_quantifiers():
    assert _safe_regex_match(r"(a+)+$", "aaaaaaaaaaaaaaaaaaaaaaaaaaaa!") is False


def test_safe_regex_match_rejects_overlong_pattern():
    assert _safe_regex_match("a" * 300, "aaa") is False


def test_safe_regex_match_invalid_pattern():
    assert _safe_regex_match(r"[unclosed", "x") is False


def test_safe_regex_match_truncates_long_input():
    assert _safe_regex_match(r"^x+$", "x" * 10000) is True


# ============ stats 缓存 ============

@pytest.mark.asyncio
async def test_alert_stats_uses_redis_cache():
    from apps.alert.routers import get_alert_stats
    from apps.alert.schemas import AlertStats

    cached = AlertStats(
        total=1,
        unique=1,
        today=0,
        firing_critical=0,
        firing_high=0,
        firing=1,
        resolved=0,
        suppressed=0,
        critical=0,
        high=0,
        medium=0,
        low=0,
        info=0,
        unassigned=0,
        aggregated=0,
    )
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=cached.model_dump_json())
    db = AsyncMock()

    result = await get_alert_stats(tenant_id=1, db=db, redis=redis)
    assert result.total == 1
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_alert_stats_miss_computes_and_sets_cache():
    from apps.alert.routers import get_alert_stats

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()

    def _row(*vals):
        m = MagicMock()
        m.one.return_value = vals
        return m

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _row(10, 2, 5, 1, 1),  # status
            _row(1, 1, 0, 0, 0, 1),  # severity
            MagicMock(scalar=lambda: 3),  # unique
            MagicMock(scalar=lambda: 2),  # today
        ]
    )

    result = await get_alert_stats(tenant_id=7, db=db, redis=redis)
    assert result.total == 10
    assert result.firing == 2
    assert redis.set.await_count == 1
    assert "alerts:stats:7" in redis.set.await_args[0][0]


# ============ 云指标 system 边界 ============

def test_require_system_admin_blocks_tenant_user():
    from apps.alert.routers import _require_system_admin
    from fastapi import HTTPException
    from apps.tenant.models import User

    user = MagicMock(spec=User)
    user.id = 5
    user.is_system = False
    with pytest.raises(HTTPException) as ei:
        _require_system_admin(user)
    assert ei.value.status_code == 403


def test_require_system_admin_allows_system():
    from apps.alert.routers import _require_system_admin
    from apps.tenant.models import User

    user = MagicMock(spec=User)
    user.id = 1
    user.is_system = True
    assert _require_system_admin(user) is user


def test_require_system_admin_allows_api_key():
    from apps.alert.routers import _require_system_admin
    from apps.tenant.models import User

    user = MagicMock(spec=User)
    user.id = 0
    user.is_system = False
    assert _require_system_admin(user) is user
