"""
SentinelX - 飞书通知渠道
"""
import json
from typing import Dict, Any, Optional
import httpx

from apps.notify.channels.base import NotificationChannel
from apps.alert.models import Alert
import structlog

logger = structlog.get_logger()


class FeishuChannel(NotificationChannel):
    """飞书通知渠道"""

    channel_type = "feishu"

    async def send(self, alert: Alert, template: str = None) -> tuple[bool, Optional[str]]:
        """发送飞书消息"""
        webhook_url = self.config.get("webhook_url")

        if not webhook_url:
            return False, "Missing webhook_url"

        try:
            # 格式化消息
            content = self.format_message(alert, template)

            # 构建消息
            message = {
                "msg_type": "text",
                "content": {
                    "text": content,
                },
            }

            # 发送请求
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(webhook_url, json=message)
                result = response.json()

            if result.get("code") == 0 or result.get("StatusCode") == 0:
                logger.info("feishu_send_success", alert_id=alert.id)
                return True, None
            else:
                error_msg = result.get("msg", result.get("error", "Unknown error"))
                logger.error("feishu_send_error", alert_id=alert.id, error=error_msg)
                return False, error_msg

        except Exception as e:
            logger.error("feishu_send_exception", alert_id=alert.id, error=str(e))
            return False, str(e)

    def get_default_template(self) -> str:
        return """【{{severity.upper()}}】{{title}}

🔔 告警详情
━━━━━━━━━━━━━━━━━
📌 来源: {{source}}
⏰ 时间: {{fired_at}}
🔢 告警ID: {{alert_id}}
🔥 触发次数: {{fire_count}}

📝 内容:
{{content}}
"""
