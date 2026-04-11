"""
SentinelX - 通知服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from apps.rule.models import NotificationRecord
from apps.notify.channels import ChannelFactory
from apps.alert.models import Alert
from apps.rule.models import NotificationChannel as ChannelModel, NotificationTemplate

logger = structlog.get_logger()


class NotificationService:
    """通知服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_alert_notifications(
        self,
        alert: Alert,
        channel_ids: List[int],
        trace_id: str = None
    ) -> Dict[int, tuple[bool, Optional[str]]]:
        """
        发送告警通知
        返回: {channel_id: (是否成功, 错误信息)}
        """
        results = {}

        # 获取配置的渠道
        for channel_id in channel_ids:
            result = await self._send_to_channel(alert, channel_id, trace_id)
            results[channel_id] = result

        return results

    async def _send_to_channel(
        self,
        alert: Alert,
        channel_id: int,
        trace_id: str = None
    ) -> tuple[bool, Optional[str]]:
        """发送到单个渠道"""
        # 获取渠道配置
        result = await self.db.execute(
            select(ChannelModel).where(ChannelModel.id == channel_id)
        )
        channel = result.scalar_one_or_none()

        if not channel:
            return False, f"Channel {channel_id} not found"

        if not channel.is_active:
            return False, f"Channel {channel_id} is inactive"

        # 获取模板
        template_result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.channel_type == channel.channel_type,
                NotificationTemplate.is_active == True,
                or_(
                    NotificationTemplate.tenant_id == str(alert.tenant_id),
                    NotificationTemplate.is_default == True
                )
            ).order_by(NotificationTemplate.is_default.desc())
        )
        template = template_result.scalar_one_or_none()
        template_content = template.content if template else None

        # 记录
        record = NotificationRecord(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            channel_id=channel_id,
            channel_type=channel.channel_type,
            status="pending",
            request_data={"alert_id": alert.id, "channel_id": channel_id},
        )
        self.db.add(record)
        await self.db.flush()

        try:
            # 发送通知
            success, error = await ChannelFactory.send_alert(
                channel.channel_type,
                channel.config,
                alert,
                template_content
            )

            # 更新记录
            record.status = "success" if success else "failed"
            record.error_message = error
            record.sent_at = datetime.utcnow()
            record.response_data = {"success": success, "error": error}

            # 更新渠道统计
            channel.send_count += 1
            if success:
                channel.success_count += 1
            else:
                channel.fail_count += 1
            channel.last_send_at = datetime.utcnow()

            await self.db.commit()

            logger.info(
                "notification_sent",
                alert_id=alert.id,
                channel_id=channel_id,
                channel_type=channel.channel_type,
                success=success,
                trace_id=trace_id
            )

            return success, error

        except Exception as e:
            record.status = "failed"
            record.error_message = str(e)
            record.retry_count += 1
            await self.db.commit()

            logger.error(
                "notification_error",
                alert_id=alert.id,
                channel_id=channel_id,
                error=str(e),
                trace_id=trace_id
            )

            return False, str(e)

    async def retry_failed_notifications(self, max_retries: int = 3) -> int:
        """重试失败的通知"""
        result = await self.db.execute(
            select(NotificationRecord).where(
                NotificationRecord.status == "failed",
                NotificationRecord.retry_count < max_retries
            )
        )
        records = result.scalars().all()

        retried = 0
        for record in records:
            # 获取告警
            alert_result = await self.db.execute(
                select(Alert).where(Alert.id == record.alert_id)
            )
            alert = alert_result.scalar_one_or_none()
            if not alert:
                continue

            success, _ = await self._send_to_channel(alert, record.channel_id)
            if success:
                retried += 1

        return retried
