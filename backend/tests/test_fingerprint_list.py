"""Tests for fingerprint aggregate list with virtual strategy group rows."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.alert.models import Alert
from apps.alert.services.fingerprint_list import (
    STRATEGY_GROUP_FP_PREFIX,
    list_alerts_fingerprint_aggregate,
)


def _make_alert(alert_id: int, **kwargs) -> Alert:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": alert_id,
        "tenant_id": "1",
        "alert_key": f"key-{alert_id}",
        "fingerprint": f"fp-{alert_id}",
        "source": "aliyun_cms",
        "title": f"Alert {alert_id}",
        "severity": "critical",
        "status": "firing",
        "labels": {},
        "annotations": {},
        "raw_data": {},
        "fire_count": 1,
        "repeat_count": 0,
        "escalation_count": 0,
        "matched_rules": [],
        "notification_channels": [],
        "fired_at": now,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Alert(**defaults)


@pytest.mark.asyncio
async def test_fingerprint_list_returns_strategy_group_and_fingerprint_rows():
    fp_row = SimpleNamespace(
        row_key="fp-a",
        row_type="fingerprint",
        group_id=None,
        group_label=None,
        latest_id=2,
        row_count=2,
        sort_at=datetime.now(timezone.utc),
    )
    sg_row = SimpleNamespace(
        row_key=f"{STRATEGY_GROUP_FP_PREFIX}2",
        row_type="strategy_group",
        group_id=2,
        group_label="test",
        latest_id=3,
        row_count=2,
        sort_at=datetime.now(timezone.utc),
    )

    total_mock = MagicMock()
    total_mock.scalar.return_value = 2

    page_mock = MagicMock()
    page_mock.all.return_value = [sg_row, fp_row]

    alert2 = _make_alert(2, fingerprint="fp-a", title="Alert 2")
    alert3 = _make_alert(3, fingerprint="fp-a", title="Parent alert")

    alerts_mock = MagicMock()
    alerts_mock.all.return_value = [
        SimpleNamespace(Alert=alert3, source_name="cms"),
        SimpleNamespace(Alert=alert2, source_name="cms"),
    ]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[total_mock, page_mock, alerts_mock])

    result = await list_alerts_fingerprint_aggregate(
        db=db,
        tenant_id="1",
        base_filter=[Alert.tenant_id == "1"],
        page=1,
        page_size=20,
    )

    assert result.total == 2
    assert len(result.items) == 2
    assert result.items[0].row_type == "strategy_group"
    assert result.items[0].aggregate_group_id == 2
    assert result.items[0].count == 2
    assert result.items[0].group_label == "test"
    assert result.items[0].fingerprint == f"{STRATEGY_GROUP_FP_PREFIX}2"
    assert result.items[0].latest.id == 3
    assert result.items[1].row_type == "fingerprint"
    assert result.items[1].count == 2
    assert result.items[1].fingerprint == "fp-a"


@pytest.mark.asyncio
async def test_fingerprint_list_empty():
    total_mock = MagicMock()
    total_mock.scalar.return_value = 0

    page_mock = MagicMock()
    page_mock.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[total_mock, page_mock])

    result = await list_alerts_fingerprint_aggregate(
        db=db,
        tenant_id="1",
        base_filter=[Alert.tenant_id == "1"],
        page=1,
        page_size=20,
    )

    assert result.total == 0
    assert result.items == []
