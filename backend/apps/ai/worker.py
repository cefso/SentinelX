"""
SentinelX - AI 异步任务 Worker（消费 alerts_ai 队列）
"""
import asyncio
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select

from apps.alert.models import Alert
from apps.ai.service import build_ai_service
from apps.ai.tasks import AI_QUEUE, update_ai_task_status
from apps.core.database import AsyncSessionLocal
from apps.core.mq import get_mq_async
from apps.core.redis import RedisClient

logger = structlog.get_logger()

AI_TASK_VT_SECONDS = 180


async def run_ai_task_by_id(task_id: str) -> None:
    """按 task_id 执行（MQ 不可用时的进程内降级）"""
    from apps.ai.tasks import _load_task

    redis = await RedisClient.get_instance()
    task = await _load_task(redis, task_id)
    if not task:
        logger.warning("ai_task_not_found", task_id=task_id)
        return
    await _execute_ai_task(redis, task)


async def _execute_ai_task(redis, task: Dict[str, Any]) -> None:
    task_id = task["task_id"]
    tenant_id = task["tenant_id"]
    alert_id = task["alert_id"]
    action = task["action"]
    params = task.get("params") or {}

    await update_ai_task_status(redis, task_id, status="running")

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Alert).where(
                    Alert.id == alert_id,
                    Alert.tenant_id == str(tenant_id),
                )
            )
            alert = result.scalar_one_or_none()
            if not alert:
                await update_ai_task_status(
                    redis, task_id, status="failed", error="Alert not found"
                )
                return

            service = await build_ai_service(db, tenant_id)
            payload, error = await _run_action(service, alert, action, params, db, tenant_id, alert_id)

            if error:
                await update_ai_task_status(redis, task_id, status="failed", error=error)
                logger.error("ai_task_failed", task_id=task_id, action=action, error=error)
                return

            await update_ai_task_status(redis, task_id, status="completed", result=payload)
            logger.info("ai_task_completed", task_id=task_id, action=action, alert_id=alert_id)

    except Exception as e:
        await update_ai_task_status(redis, task_id, status="failed", error=str(e))
        logger.error("ai_task_exception", task_id=task_id, error=str(e), exc_info=True)


async def _run_action(
    service,
    alert: Alert,
    action: str,
    params: Dict[str, Any],
    db,
    tenant_id: int,
    alert_id: int,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    if action == "analyze":
        analysis, error = await service.analyze_root_cause(alert)
        if error:
            return None, f"Analysis failed: {error}"
        return {"alert_id": alert_id, "analysis": analysis}, None

    if action == "polish":
        polished, error = await service.polish_content(
            alert,
            params.get("template"),
            params.get("style", "formal"),
        )
        if error:
            return None, f"Polish failed: {error}"
        return {"alert_id": alert_id, "polished_content": polished}, None

    if action == "suggest-actions":
        history_result = await db.execute(
            select(Alert).where(
                Alert.tenant_id == str(tenant_id),
                Alert.alert_key == alert.alert_key,
                Alert.id != alert_id,
            ).order_by(Alert.fired_at.desc()).limit(10)
        )
        history = [
            {
                "title": a.title,
                "status": a.status,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in history_result.scalars().all()
        ]
        content, error = await service.suggest_actions(alert, history)
        if error:
            return None, f"Suggestion failed: {error}"
        return {
            "alert_id": alert_id,
            "suggestion_content": content,
        }, None

    if action == "predict-impact":
        impact, error = await service.predict_impact(alert)
        if error:
            return None, f"Prediction failed: {error}"
        return {"alert_id": alert_id, "predicted_impact": impact}, None

    return None, f"Unknown AI action: {action}"


class AIWorker:
    """消费 alerts_ai 队列"""

    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        logger.info("ai_worker_started")
        backoff = 1
        max_backoff = 30

        while self.running:
            try:
                processed = await self.process_one()
                if processed:
                    backoff = 1
                else:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
            except Exception as e:
                logger.error("ai_worker_error", error=str(e))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def stop(self):
        self.running = False
        logger.info("ai_worker_stopped")

    async def process_one(self) -> bool:
        mq = await get_mq_async()
        msg = await mq.receive(AI_QUEUE, count=1, vt=AI_TASK_VT_SECONDS)
        if not msg:
            return False

        message = msg.message
        task_id = message.get("task_id")
        if not task_id:
            await mq.ack(AI_QUEUE, msg.msg_id)
            return True

        redis = await RedisClient.get_instance()
        from apps.ai.tasks import _load_task

        task = await _load_task(redis, task_id)
        if not task:
            task = message

        try:
            await _execute_ai_task(redis, task)
            await mq.ack(AI_QUEUE, msg.msg_id)
        except Exception as e:
            logger.error("ai_worker_message_error", task_id=task_id, error=str(e))
            await mq.nack(AI_QUEUE, msg.msg_id, vt=60)
        return True
