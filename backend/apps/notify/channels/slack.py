"""
SentinelX - Slack通知渠道
"""
from typing import Optional
import httpx

from apps.notify.channels.base import NotificationChannel
from apps.alert.models import Alert
import structlog

logger = structlog.get_logger()

SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#ca8a04",
    "low": "#2563eb",
    "info": "#6b7280",
}


class SlackChannel(NotificationChannel):
    """Slack通知渠道 (Incoming Webhooks)"""

    channel_type = "slack"

    async def send(self, alert: Alert, template: str = None) -> tuple[bool, Optional[str]]:
        """发送Slack消息"""
        webhook_url = self.config.get("webhook_url")

        if not webhook_url:
            return False, "Missing webhook_url"

        try:
            color = SEVERITY_COLORS.get(alert.severity, "#6b7280")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": f"[{alert.severity.upper()}] {alert.title}",
                                },
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {"type": "mrkdwn", "text": f"*Source:*\n{alert.source}"},
                                    {"type": "mrkdwn", "text": f"*Status:*\n{alert.status}"},
                                    {"type": "mrkdwn", "text": f"*Alert ID:*\n{alert.id}"},
                                    {"type": "mrkdwn", "text": f"*Fire Count:*\n{alert.fire_count}"},
                                ],
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*Content:*\n{alert.content or 'N/A'}",
                                },
                            },
                        ],
                    }
                ]
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(webhook_url, json=payload)

            if response.status_code == 200:
                logger.info("slack_send_success", alert_id=alert.id)
                return True, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error("slack_send_error", alert_id=alert.id, error=error_msg)
                return False, error_msg

        except Exception as e:
            logger.error("slack_send_exception", alert_id=alert.id, error=str(e))
            return False, str(e)

    def get_default_template(self) -> str:
        return ""
