"""
升级检查 IO 优化测试：分批 LIMIT + 批量 last notification
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.alert.models import Alert
from apps.alert.services.escalation import EscalationService


def _firing_alert(alert_id: int, escalation_count: int = 0, hours_ago: float = 2.0) -> Alert:
    a = Alert(
        tenant_id=1,
        alert_key=f"k{alert_id}",
        fingerprint=f"fp{alert_id}",
        source="test",
        title=f"t{alert_id}",
        severity="high",
        status="firing",
        escalation_count=escalation_count,
        fired_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    )
    a.id = alert_id
    a.acknowledged_at = None
    return a


def _result(*, scalars_values=None, all_rows=None):
    r = MagicMock()
    if scalars_values is not None:
        r.scalars.return_value.all.return_value = scalars_values
    if all_rows is not None:
        r.all.return_value = all_rows
    return r


@pytest.mark.asyncio
async def test_check_escalations_batches_last_notification_query():
    """N 条候选告警只应有一次 last-notification 聚合查询，而非 per-alert N+1"""
    alerts = [_firing_alert(i, hours_ago=3) for i in range(1, 6)]

    db = AsyncMock()
    # 第一次：候选告警；第二次：批量 last notification
    candidates = _result(scalars_values=alerts)
    last_notif = _result(all_rows=[])
    db.execute = AsyncMock(side_effect=[candidates, last_notif])
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = EscalationService(db)
    stats = await service.check_escalations(tenant_id=1)

    # 候选 + last notification = 2 次 execute
    assert db.execute.await_count == 2
    # 已超过等待时间应升级
    assert stats["escalated_count"] == 5
    # 批量升级一次 commit
    assert db.commit.await_count == 1
    assert db.add.call_count == 5


@pytest.mark.asyncio
async def test_check_escalations_applies_limit_and_tenant_filter():
    alerts = [_firing_alert(1, hours_ago=3)]
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _result(scalars_values=alerts),
        _result(all_rows=[]),
    ])
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = EscalationService(db)
    await service.check_escalations(tenant_id=7, batch_size=50, lookback_hours=6)

    # 验证查询被调用（编译参数在 mock 下难以断言，至少保证路径可跑）
    assert db.execute.await_count == 2
    # 签名兼容：手动触发路由仍只传 tenant_id
    import inspect
    sig = inspect.signature(EscalationService.check_escalations)
    assert "tenant_id" in sig.parameters
    assert "batch_size" in sig.parameters
    assert "lookback_hours" in sig.parameters


@pytest.mark.asyncio
async def test_check_escalations_skips_recent_notification():
    """最近刚通知过的告警不应升级"""
    alert = _firing_alert(1, hours_ago=3)
    db = AsyncMock()
    now = datetime.now(timezone.utc)
    last_row = MagicMock()
    last_row.alert_id = 1
    last_row.last_at = now  # 刚通知
    db.execute = AsyncMock(side_effect=[
        _result(scalars_values=[alert]),
        _result(all_rows=[last_row]),
    ])
    db.add = MagicMock()
    db.commit = AsyncMock()

    service = EscalationService(db)
    stats = await service.check_escalations(tenant_id=1)

    assert stats["escalated_count"] == 0
    db.commit.assert_not_awaited()
    db.add.assert_not_called()


def test_should_escalate_uses_preloaded_last_notification():
    service = EscalationService(db=AsyncMock())
    alert = _firing_alert(1, escalation_count=0, hours_ago=1)
    now = datetime.now(timezone.utc)

    # 刚通知过 → 不升级
    ok, wait = service._should_escalate(alert, last_notification=now)
    assert ok is False
    assert wait > 0

    # 无通知记录且 fired 超过 5 分钟 → 升级
    ok, _ = service._should_escalate(alert, last_notification=None)
    assert ok is True


@pytest.mark.asyncio
async def test_get_last_notification_times_empty():
    service = EscalationService(db=AsyncMock())
    assert await service._get_last_notification_times([]) == {}
