"""
SentinelX - 告警源 API 测试
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from apps.alert.models import AlertSource
from apps.alert.schemas import AlertSourceUpdate
from apps.alert.routers import update_source


@pytest.mark.asyncio
async def test_alert_source_update_schema_accepts_active_inactive():
    body = AlertSourceUpdate(name="Updated", is_active="inactive")
    assert body.is_active == "inactive"


def test_alert_source_update_schema_rejects_invalid_status():
    with pytest.raises(ValidationError):
        AlertSourceUpdate(is_active="enabled")


def _make_source(**kwargs) -> AlertSource:
    defaults = dict(
        id=1,
        tenant_id=10,
        name="Original",
        code="prom-01",
        source_type="prometheus",
        config={"k": "v"},
        client_id="abc12345",
        is_active="active",
        alert_count=0,
        description=None,
    )
    defaults.update(kwargs)
    source = AlertSource(**{k: v for k, v in defaults.items() if k != "id"})
    source.id = defaults["id"]
    return source


@pytest.mark.asyncio
async def test_update_source_applies_fields():
    source = _make_source()
    db = AsyncMock()
    db.get = AsyncMock(return_value=source)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    body = AlertSourceUpdate(
        name="Renamed",
        description="desc",
        is_active="inactive",
        config={"k": "v2"},
    )
    updated = await update_source(1, body, tenant_id=10, db=db)

    assert updated.name == "Renamed"
    assert updated.description == "desc"
    assert updated.is_active == "inactive"
    assert updated.config == {"k": "v2"}
    assert updated.client_id == "abc12345"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_source_wrong_tenant_returns_404():
    source = _make_source(tenant_id=10)
    db = AsyncMock()
    db.get = AsyncMock(return_value=source)

    with pytest.raises(HTTPException) as exc:
        await update_source(1, AlertSourceUpdate(name="X"), tenant_id=99, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_source_duplicate_code_returns_409():
    source = _make_source(id=2, code="code-b")
    other = _make_source(id=1, code="code-a")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = other

    db = AsyncMock()
    db.get = AsyncMock(return_value=source)
    db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(HTTPException) as exc:
        await update_source(2, AlertSourceUpdate(code="code-a"), tenant_id=10, db=db)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_source_not_found_returns_404():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await update_source(999, AlertSourceUpdate(name="X"), tenant_id=10, db=db)
    assert exc.value.status_code == 404
