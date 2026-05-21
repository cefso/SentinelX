"""
SentinelX - 告警 AI 异步任务（Redis 状态 + PGMQ 队列）
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.alert.models import Alert
from apps.ai.config import resolve_tenant_ai_config
from apps.core.mq import get_mq_async

logger = structlog.get_logger()

TASK_KEY_PREFIX = "ai:task:"
TASK_TTL_SECONDS = 3600
AI_QUEUE = "alerts_ai"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _load_task(redis: Redis, task_id: str) -> Optional[Dict[str, Any]]:
    raw = await redis.get(f"{TASK_KEY_PREFIX}{task_id}")
    if not raw:
        return None
    return json.loads(raw)


async def _save_task(redis: Redis, task: Dict[str, Any]) -> None:
    await redis.set(
        f"{TASK_KEY_PREFIX}{task['task_id']}",
        json.dumps(task),
        ex=TASK_TTL_SECONDS,
    )


async def create_ai_task(
    redis: Redis,
    tenant_id: int,
    alert_id: int,
    action: str,
    params: Optional[Dict[str, Any]] = None,
) -> str:
    task_id = str(uuid.uuid4())
    now = _utc_now()
    task = {
        "task_id": task_id,
        "tenant_id": tenant_id,
        "alert_id": alert_id,
        "action": action,
        "params": params or {},
        "status": "pending",
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    await _save_task(redis, task)
    return task_id


async def get_ai_task_for_tenant(
    redis: Redis,
    task_id: str,
    tenant_id: int,
) -> Dict[str, Any]:
    task = await _load_task(redis, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI task not found")
    if task.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return task


async def update_ai_task_status(
    redis: Redis,
    task_id: str,
    *,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    task = await _load_task(redis, task_id)
    if not task:
        return
    task["status"] = status
    task["updated_at"] = _utc_now()
    if result is not None:
        task["result"] = result
    if error is not None:
        task["error"] = error
    await _save_task(redis, task)


async def enqueue_ai_task(
    task_id: str,
    tenant_id: int,
    alert_id: int,
    action: str,
    params: Optional[Dict[str, Any]] = None,
) -> None:
    message = {
        "task_id": task_id,
        "tenant_id": tenant_id,
        "alert_id": alert_id,
        "action": action,
        "params": params or {},
    }
    try:
        mq = await get_mq_async()
        await mq.send(AI_QUEUE, message)
    except Exception as e:
        logger.warning("ai_task_mq_enqueue_failed", task_id=task_id, error=str(e))
        from apps.ai.worker import run_ai_task_by_id

        asyncio.create_task(run_ai_task_by_id(task_id))


async def submit_alert_ai_task(
    db: AsyncSession,
    redis: Redis,
    tenant_id: int,
    alert_id: int,
    action: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """校验告警与 AI 配置，创建任务并入队"""
    await resolve_tenant_ai_config(db, tenant_id)

    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == str(tenant_id),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    task_id = await create_ai_task(redis, tenant_id, alert_id, action, params)
    await enqueue_ai_task(task_id, tenant_id, alert_id, action, params)
    return {
        "task_id": task_id,
        "status": "pending",
        "alert_id": alert_id,
        "action": action,
    }
