"""第四轮：overview 合并、dispose silence、注册防枚举、API Key 溯源"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.alert.schemas import AlertOverviewResponse, AlertStats, DisposeRequest


def test_dispose_request_accepts_silence_minutes():
    req = DisposeRequest(action="silence", comment="mute", silence_minutes=120)
    assert req.silence_minutes == 120


def test_dispose_request_silence_minutes_bounds():
    with pytest.raises(Exception):
        DisposeRequest(action="silence", comment="x", silence_minutes=0)
    with pytest.raises(Exception):
        DisposeRequest(action="silence", comment="x", silence_minutes=10081)


def test_alert_overview_schema_shape():
    stats = AlertStats(
        total=1, unique=1, today=0, firing_critical=0, firing_high=0,
        firing=1, resolved=0, suppressed=0, critical=0, high=0,
        medium=0, low=0, info=0, unassigned=0, aggregated=0,
    )
    ov = AlertOverviewResponse(stats=stats, firing_dedup=1, critical_dedup=0, high_dedup=0)
    assert ov.stats.firing == 1


@pytest.mark.asyncio
async def test_dispose_silence_sets_status_and_silenced_until():
    from apps.alert.routers import dispose_alert
    from apps.alert.models import Alert
    from apps.tenant.models import User

    alert = MagicMock(spec=Alert)
    alert.id = 9
    alert.tenant_id = 1
    alert.status = "firing"
    alert.acknowledged_at = None
    alert.resolved_at = None
    alert.silenced_until = None

    user = MagicMock(spec=User)
    user.id = 1
    user.username = "admin"

    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = alert
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    req = DisposeRequest(action="silence", comment="pause", silence_minutes=30)
    await dispose_alert(alert_id=9, request=req, tenant_id=1, db=db, current_user=user)

    assert alert.status == "suppressed"
    assert alert.silenced_until is not None
    assert alert.silenced_until > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_register_uses_unified_error_message():
    from apps.auth.services.auth import AuthService
    from apps.core.exceptions import AuthenticationError
    from apps.tenant.models import User

    db = AsyncMock()

    def _hit_username(*a, **k):
        m = MagicMock()
        m.scalar_one_or_none.return_value = 1
        return m

    db.execute = AsyncMock(side_effect=_hit_username)
    svc = AuthService(db)
    with pytest.raises(AuthenticationError) as ei:
        await svc.register(username="taken", email="a@b.com", password="Password@1")
    assert "username or email is not available" in str(ei.value).lower() or \
           "username or email is not available" in ei.value.args[0].lower()


@pytest.mark.asyncio
async def test_create_api_key_records_created_by():
    from apps.auth.api_key import APIKeyAuth
    from apps.tenant.models import Tenant, APIKey

    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.api_token = "{}"

    db = AsyncMock()
    t_result = MagicMock()
    t_result.scalar_one_or_none.return_value = tenant
    db.execute = AsyncMock(return_value=t_result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    auth = APIKeyAuth(db)
    api_key, full = await auth.create_api_key(
        tenant_id=1, name="t", expires_days=None, created_by=42
    )
    added = db.add.call_args[0][0]
    assert isinstance(added, APIKey) or added.created_by == 42
    assert added.created_by == 42


def test_api_key_model_has_created_by():
    from apps.tenant.models import APIKey
    assert hasattr(APIKey, "created_by")


def test_api_key_migration_exists():
    from pathlib import Path
    p = Path("/Users/cefso/code/SentinelX/.worktrees/audit-code-quality/backend/alembic/versions/20260918_api_key_created_by.py")
    assert p.exists()
    text = p.read_text()
    assert "created_by" in text
