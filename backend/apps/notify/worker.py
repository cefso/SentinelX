"""
SentinelX - 通知Worker
处理通知队列中的消息
"""
import asyncio
from typing import List, Dict, Any
import structlog

from apps.core.database import AsyncSessionLocal as async_session_factory
from sqlalchemy import select
from apps.core.mq import get_mq_async
from apps.notify.services.sender import NotificationService
from apps.alert.models import Alert

logger = structlog.get_logger()


class NotificationWorker:
    """通知Worker - 从 PGMQ 队列消费并发送通知"""

    def __init__(self):
        self.running = False

    async def start(self):
        """启动Worker"""
        self.running = True
        logger.info("notification_worker_started")

        backoff = 1  # 指数退避起始值（秒）
        max_backoff = 30  # 最大退避时间

        while self.running:
            try:
                received = await self.process_queue()
                if received:
                    backoff = 1  # 收到消息，重置退避
                else:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
            except Exception as e:
                logger.error("worker_error", error=str(e))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def stop(self):
        """停止Worker"""
        self.running = False
        logger.info("notification_worker_stopped")

    async def process_queue(self) -> bool:
        """从 PGMQ 消费通知消息，返回是否收到消息"""
        mq = await get_mq_async()

        msg = await mq.receive("alerts_notify", count=1, vt=300)
        if not msg:
            return False

        notification = msg.message
        try:
            await self.send_notification(notification)
            await mq.ack("alerts_notify", msg.msg_id)
        except Exception as e:
            logger.error("notification_processing_error", error=str(e))
            await mq.nack("alerts_notify", msg.msg_id, vt=60)
        return True

    async def send_notification(self, notification: Dict[str, Any]):
        """发送单个通知"""
        is_test = notification.get("is_test", False)

        if is_test:
            await self._send_test_notification(notification)
            return

        alert_id = notification.get("alert_id")
        channel_ids = notification.get("channels", [])
        template_map = notification.get("template_map", {})
        trace_id = notification.get("trace_id")

        if not alert_id or not channel_ids:
            logger.warning("invalid_notification", alert_id=alert_id, channels=channel_ids)
            return

        async with async_session_factory() as db:
            service = NotificationService(db)

            # 获取告警
            from sqlalchemy import select

            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()

            if not alert:
                logger.warning("alert_not_found", alert_id=alert_id)
                return

            # 发送通知
            results = await service.send_alert_notifications(alert, channel_ids, template_map, trace_id)

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

    async def _send_test_notification(self, notification: Dict[str, Any]):
        """发送测试通知（不走数据库查告警）"""
        record_id = notification.get("record_id")
        channel_type = notification.get("channel_type")
        channel_config = notification.get("channel_config")
        content = notification.get("content", "")
        title = notification.get("title", "[测试消息]")
        template_content = notification.get("template_content")

        from apps.rule.models import NotificationRecord as RecordModel

        async with async_session_factory() as db:
            from datetime import datetime, timezone
            from apps.notify.channels import ChannelFactory

            # 构建测试用Alert对象（内存中，不存数据库）
            test_alert = Alert(
                tenant_id=notification.get("tenant_id", 0),
                alert_key=f"test-record-{record_id}",
                fingerprint=f"test-fp-{record_id}",
                source="test",
                title=title,
                content=content,
                severity="info",
                status="firing",
                labels={},
                annotations={},
            )
            test_alert.fire_count = 1
            test_alert.id = 0  # 标记为测试

            # 发送通知
            success, error = await ChannelFactory.send_alert(
                channel_type,
                channel_config,
                test_alert,
                template_content,
            )

            # 更新记录状态
            if record_id:
                result = await db.execute(select(RecordModel).where(RecordModel.id == record_id))
                record = result.scalar_one_or_none()
                if record:
                    record.status = "success" if success else "failed"
                    record.error_message = error
                    record.sent_at = datetime.utcnow()
                    record.response_data = {
                        "success": success,
                        "error": error,
                        "channel_type": channel_type,
                        "is_test": True,
                    }
                    await db.commit()

            logger.info(
                "test_notification_result",
                record_id=record_id,
                channel_type=channel_type,
                success=success,
                error=error
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
