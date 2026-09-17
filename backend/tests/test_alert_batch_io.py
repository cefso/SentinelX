"""
批量接警 IO 优化测试：一条 SELECT 预取指纹 + 一次 flush/commit
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.alert.models import AlertHistory
from apps.alert.routers import _create_alert_batch, _create_single_alert
from apps.alert.schemas import AlertCreate


def _make_alert_create(key: str, fingerprint: str = "fp-1") -> AlertCreate:
    return AlertCreate(
        alert_key=key,
        source="test",
        title=f"title-{key}",
        severity="high",
        fingerprint=fingerprint,
    )


def _result(scalars_values=None, all_rows=None):
    r = MagicMock()
    if scalars_values is not None:
        r.scalars.return_value.all.return_value = scalars_values
    if all_rows is not None:
        r.all.return_value = all_rows
    return r


@pytest.mark.asyncio
async def test_create_alert_batch_single_select_single_flush_single_commit():
    """N 条告警只应有一次指纹预取 SELECT、一次 flush、一次 commit"""
    alerts = [_make_alert_create(f"k{i}", fingerprint=f"fp-{i}") for i in range(5)]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result(scalars_values=[]))
    db.add_all = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    mq = AsyncMock()
    mq.send = AsyncMock(return_value=1)

    with patch("apps.alert.routers.get_mq_async", AsyncMock(return_value=mq)):
        result = await _create_alert_batch(alerts, tenant_id=1, db=db, redis=None)

    assert result["received"] == 5
    assert len(result["alerts"]) == 5
    # 一条预取 SELECT
    assert db.execute.await_count == 1
    # 一次 flush / 一次 commit
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    # 5 条 alert 一次 add_all
    db.add_all.assert_called_once()
    assert len(db.add_all.call_args[0][0]) == 5
    # MQ 逐条 send（不支持批量），共 5 次，但无额外 commit
    assert mq.send.await_count == 5
    assert db.commit.await_count == 1
    # history 5 条
    assert db.add.call_count == 5


@pytest.mark.asyncio
async def test_create_alert_batch_history_action_received_then_fired():
    """同批相同指纹：首条 received，后续 fired；已有活跃指纹则全部 fired"""
    same_fp = [
        _make_alert_create("a", fingerprint="fp-same"),
        _make_alert_create("b", fingerprint="fp-same"),
    ]
    new_fp = [_make_alert_create("c", fingerprint="fp-new")]

    db = AsyncMock()
    # 已有 fp-same 活跃
    db.execute = AsyncMock(return_value=_result(scalars_values=["fp-same"]))
    db.add_all = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    # 模拟 flush 后 id 赋值
    def _assign_ids(objs):
        for i, a in enumerate(objs, start=1):
            a.id = i

    db.add_all.side_effect = lambda objs: _assign_ids(objs)

    mq = AsyncMock()
    mq.send = AsyncMock(return_value=1)

    with patch("apps.alert.routers.get_mq_async", AsyncMock(return_value=mq)):
        await _create_alert_batch(same_fp + new_fp, tenant_id=1, db=db, redis=None)

    histories = [c[0][0] for c in db.add.call_args_list]
    actions = [h.action for h in histories]
    assert actions == ["fired", "fired", "received"]
    assert all(isinstance(h, AlertHistory) for h in histories)


@pytest.mark.asyncio
async def test_create_single_alert_does_not_commit():
    """单条路径复用批量逻辑但不 commit，由调用方收口"""
    alert_data = _make_alert_create("solo", fingerprint="fp-solo")

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result(scalars_values=[]))
    db.add_all = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    def _assign_ids(objs):
        for i, a in enumerate(objs, start=1):
            a.id = i

    db.add_all.side_effect = lambda objs: _assign_ids(objs)

    mq = AsyncMock()
    mq.send = AsyncMock(return_value=1)

    with patch("apps.alert.routers.get_mq_async", AsyncMock(return_value=mq)):
        result = await _create_single_alert(alert_data, tenant_id=1, db=db, redis=None)

    assert result["id"] == 1
    assert result["trace_id"]
    db.commit.assert_not_awaited()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_alert_batch_empty():
    db = AsyncMock()
    result = await _create_alert_batch([], tenant_id=1, db=db, redis=None)
    assert result == {"received": 0, "alerts": []}
    db.execute.assert_not_awaited()
    db.commit.assert_not_awaited()
