"""
SentinelX - 钉钉通知渠道
"""
import hashlib
import hmac
import time
import base64
import json
from typing import Dict, Any, Optional
import httpx

from apps.notify.channels.base import NotificationChannel
from apps.alert.models import Alert
import structlog

logger = structlog.get_logger()


class DingTalkChannel(NotificationChannel):
    """钉钉通知渠道"""

    channel_type = "dingtalk"

    async def send(self, alert: Alert, template: str = None) -> tuple[bool, Optional[str]]:
        """
        发送钉钉消息
        支持加签和普通模式
        """
        webhook_url = self.config.get("webhook_url")
        secret = self.config.get("secret")

        if not webhook_url:
            return False, "Missing webhook_url"

        try:
            # 格式化消息
            content = self.format_message(alert, template)

            # 构建 markdown 消息
            # 解析 content，格式：标题\n---\n内容
            parts = content.split("\n---\n", 1)
            title = parts[0] if parts else "告警通知"
            text = parts[1] if len(parts) > 1 else content

            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": text,
                },
            }

            # 如果配置了密钥，使用加签模式
            if secret:
                timestamp, sign = self._generate_sign(secret)
                url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
            else:
                url = webhook_url

            # 发送请求
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=message)
                result = response.json()

            if result.get("errcode") == 0:
                logger.info("dingtalk_send_success", alert_id=alert.id)
                return True, None
            else:
                error_msg = result.get("errmsg", "Unknown error")
                logger.error("dingtalk_send_error", alert_id=alert.id, error=error_msg)
                return False, error_msg

        except Exception as e:
            logger.error("dingtalk_send_exception", alert_id=alert.id, error=str(e))
            return False, str(e)

    def _generate_sign(self, secret: str) -> tuple[str, str]:
        """生成加签"""
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{secret}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return timestamp, sign

    def get_default_template(self) -> str:
        return """### 【{{severity.upper()}}】{{title}}
---
> 来源: **{{source}}** | 时间: **{{fired_at}}** | ID: **{{alert_id}}** | 触发: **{{fire_count}}次**

**内容:**
{{content}}
"""
