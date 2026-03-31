"""
SentinelX - Webhook通知渠道
"""
from typing import Dict, Any, Optional
import httpx
import json

from apps.notify.channels.base import NotificationChannel
from apps.alert.models import Alert
import structlog

logger = structlog.get_logger()


class WebhookChannel(NotificationChannel):
    """通用Webhook通知渠道"""

    channel_type = "webhook"

    async def send(self, alert: Alert, template: str = None) -> tuple[bool, Optional[str]]:
        """发送Webhook请求"""
        webhook_url = self.config.get("webhook_url")
        headers = self.config.get("headers", {})

        if not webhook_url:
            return False, "Missing webhook_url"

        try:
            # 格式化消息
            content = self.format_message(alert, template)

            # 构建请求体
            payload = {
                "alert_id": alert.id,
                "title": alert.title,
                "content": content,
                "severity": alert.severity,
                "source": alert.source,
                "status": alert.status,
                "alert_key": alert.alert_key,
                "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
                "fire_count": alert.fire_count,
                "labels": alert.labels or {},
                "annotations": alert.annotations or {},
                "metric_name": alert.metric_name,
                "metric_value": alert.metric_value,
            }

            # 发送请求
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                )

            if response.status_code >= 200 and response.status_code < 300:
                logger.info("webhook_send_success", alert_id=alert.id, status=response.status_code)
                return True, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error("webhook_send_error", alert_id=alert.id, error=error_msg)
                return False, error_msg

        except Exception as e:
            logger.error("webhook_send_exception", alert_id=alert.id, error=str(e))
            return False, str(e)

    def get_default_template(self) -> str:
        # Webhook默认不使用模板，直接发送JSON
        return ""
