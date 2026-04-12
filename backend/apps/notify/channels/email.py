"""
SentinelX - 邮件通知渠道
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

from apps.notify.channels.base import NotificationChannel
from apps.alert.models import Alert
import structlog

logger = structlog.get_logger()


class EmailChannel(NotificationChannel):
    """邮件通知渠道"""

    channel_type = "email"

    async def send(self, alert: Alert, template: str = None) -> tuple[bool, Optional[str]]:
        """发送邮件"""
        smtp_host = self.config.get("smtp_host")
        smtp_port = self.config.get("smtp_port", 587)
        username = self.config.get("username")
        password = self.config.get("password")
        from_addr = self.config.get("from_addr")
        recipients = self.config.get("recipients", "")

        if not all([smtp_host, username, password, from_addr, recipients]):
            return False, "Missing email configuration"

        try:
            # 格式化消息
            content = self.format_message(alert, template)

            # 构建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.upper()}] {alert.title}"
            msg["From"] = from_addr
            msg["To"] = recipients

            # 添加纯文本版本
            text_part = MIMEText(content, "plain", "utf-8")
            msg.attach(text_part)

            # 添加HTML版本
            html_content = self._generate_html(alert, template)
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            # 使用 asyncio.to_thread 避免阻塞事件循环
            await asyncio.to_thread(
                self._send_smtp, smtp_host, smtp_port, username, password,
                from_addr, recipients, msg
            )

            logger.info("email_send_success", alert_id=alert.id)
            return True, None

        except Exception as e:
            logger.error("email_send_exception", alert_id=alert.id, error=str(e))
            return False, str(e)

    @staticmethod
    def _send_smtp(smtp_host, smtp_port, username, password, from_addr, recipients, msg):
        """同步发送 SMTP 邮件（在单独线程中运行）"""
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(from_addr, recipients.split(","), msg.as_string())

    def _generate_html(self, alert: Alert, template: str = None) -> str:
        """生成HTML格式"""
        severity_colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#ca8a04",
            "low": "#2563eb",
            "info": "#6b7280",
        }
        color = severity_colors.get(alert.severity, "#6b7280")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {color}; color: white; padding: 15px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
        .field {{ margin: 10px 0; }}
        .label {{ color: #6b7280; font-size: 12px; }}
        .value {{ font-size: 14px; }}
        .alert-content {{ background: white; padding: 15px; border-radius: 4px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin:0;">【{alert.severity.upper()}】 {alert.title}</h2>
        </div>
        <div class="content">
            <div class="field">
                <div class="label">来源</div>
                <div class="value">{alert.source}</div>
            </div>
            <div class="field">
                <div class="label">时间</div>
                <div class="value">{alert.fired_at.strftime('%Y-%m-%d %H:%M:%S') if alert.fired_at else ''}</div>
            </div>
            <div class="field">
                <div class="label">告警ID</div>
                <div class="value">{alert.id}</div>
            </div>
            <div class="field">
                <div class="label">触发次数</div>
                <div class="value">{alert.fire_count}</div>
            </div>
            <div class="alert-content">
                <div class="label">告警内容</div>
                <div class="value">{alert.content or '无'}</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

    def get_default_template(self) -> str:
        return """【{{severity.upper()}}】{{title}}

来源: {{source}}
时间: {{fired_at}}
告警ID: {{alert_id}}
触发次数: {{fire_count}}

内容:
{{content}}
"""
