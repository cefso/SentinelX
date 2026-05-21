"""
SentinelX - AI 异步任务测试
"""
import json
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from apps.ai.tasks import (
    TASK_KEY_PREFIX,
    create_ai_task,
    get_ai_task_for_tenant,
    update_ai_task_status,
)


@pytest.mark.asyncio
async def test_create_and_get_ai_task():
    store = {}

    async def mock_get(key):
        return store.get(key)

    async def mock_set(key, value, ex=None):
        store[key] = value

    redis = AsyncMock()
    redis.get = mock_get
    redis.set = mock_set

    task_id = await create_ai_task(redis, tenant_id=1, alert_id=34, action="analyze")
    task = await get_ai_task_for_tenant(redis, task_id, tenant_id=1)

    assert task["task_id"] == task_id
    assert task["status"] == "pending"
    assert task["alert_id"] == 34
    assert task["action"] == "analyze"


@pytest.mark.asyncio
async def test_get_ai_task_wrong_tenant():
    store = {}

    async def mock_get(key):
        return store.get(key)

    async def mock_set(key, value, ex=None):
        store[key] = value

    redis = AsyncMock()
    redis.get = mock_get
    redis.set = mock_set

    task_id = await create_ai_task(redis, tenant_id=1, alert_id=34, action="analyze")

    with pytest.raises(HTTPException) as exc:
        await get_ai_task_for_tenant(redis, task_id, tenant_id=2)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_ai_task_status():
    store = {}

    async def mock_get(key):
        return store.get(key)

    async def mock_set(key, value, ex=None):
        store[key] = value

    redis = AsyncMock()
    redis.get = mock_get
    redis.set = mock_set

    task_id = await create_ai_task(redis, tenant_id=1, alert_id=34, action="polish")
    await update_ai_task_status(
        redis,
        task_id,
        status="completed",
        result={"alert_id": 34, "polished_content": "ok"},
    )

    raw = store[f"{TASK_KEY_PREFIX}{task_id}"]
    task = json.loads(raw)
    assert task["status"] == "completed"
    assert task["result"]["polished_content"] == "ok"
