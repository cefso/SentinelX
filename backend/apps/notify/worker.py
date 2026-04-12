"""
SentinelX - 通知Worker
处理通知队列中的消息
"""
import asyncio
from typing import List, Dict, Any
import structlog

from apps.core.database import AsyncSessionLocal as async_session_factory
from apps.core.mq import get_mq_async
from apps.notify.services.sender import NotificationService

logger = structlog.get_logger()


class NotificationWorker:
    """通知Worker - 从 PGMQ 队列消费并发送通知"""

    def __init__(self):
        self.running = False

    async def start(self):
        """启动Worker"""
        self.running = True
        logger.info("notification_worker_started")

        while self.running:
            try:
                await self.process_queue()
            except Exception as e:
                logger.error("worker_error", error=str(e))
                await asyncio.sleep(5)

    async def stop(self):
        """停止Worker"""
        self.running = False
        logger.info("notification_worker_stopped")

    async def process_queue(self):
        """从 PGMQ 消费通知消息"""
        mq = await get_mq_async()

        msg = await mq.receive("alerts_notify", count=1, vt=300)
        if not msg:
            return

        notification = msg.message
        try:
            await self.send_notification(notification)
            await mq.ack("alerts_notify", msg.msg_id)
        except Exception as e:
            logger.error("notification_processing_error", error=str(e))
            await mq.nack("alerts_notify", msg.msg_id, vt=60)

    async def send_notification(self, notification: Dict[str, Any]):
        """发送单个通知"""
        alert_id = notification.get("alert_id")
        channel_ids = notification.get("channels", [])
        trace_id = notification.get("trace_id")

        if not alert_id or not channel_ids:
            logger.warning("invalid_notification", alert_id=alert_id, channels=channel_ids)
            return

        async with async_session_factory() as db:
            service = NotificationService(db)

            # 获取告警
            from sqlalchemy import select
            from apps.alert.models import Alert

            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()

            if not alert:
                logger.warning("alert_not_found", alert_id=alert_id)
                return

            # 发送通知
            results = await service.send_alert_notifications(alert, channel_ids, trace_id)

            # 记录结果
            for channel_id, (success, error) in results.items():
                if success:
                    logger.info(
                        "notification_delivered",
                        alert_id=alert_id,
                        channel_id=channel_id,
                        trace_id=trace_id
                    )
                else:
                    logger.error(
                        "notification_failed",
                        alert_id=alert_id,
                        channel_id=channel_id,
                        error=error,
                        trace_id=trace_id
                    )


async def run_worker():
    """运行Worker"""
    worker = NotificationWorker()
    try:
        await worker.start()
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
