"""
告警恢复（OK）时解析 firing / suppressed 状态
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.alert.models import Alert
from apps.alert.routers import _resolve_firing_alerts


def _alert(status: str, fingerprint: str = "fp-test") -> Alert:
    now = datetime.now(timezone.utc)
    return Alert(
        tenant_id="1",
        fingerprint=fingerprint,
        status=status,
        severity="high",
        source="test",
        title="t",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_resolve_firing_alerts_includes_suppressed():
    firing = _alert("firing")
    firing.id = 1
    suppressed = _alert("suppressed")
    suppressed.id = 2

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [firing, suppressed]

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    count = await _resolve_firing_alerts(mock_db, "1", ["fp-test"])

    assert count == 2
    assert firing.status == "resolved"
    assert suppressed.status == "resolved"
    assert firing.resolved_at is not None
    assert suppressed.resolved_at is not None
    mock_db.commit.assert_awaited_once()
