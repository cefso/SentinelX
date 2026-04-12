"""
SentinelX - 通知渠道基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import structlog

from apps.alert.models import Alert

logger = structlog.get_logger()


class NotificationChannel(ABC):
    """通知渠道基类"""

    channel_type: str = "base"

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def send(self, alert: Alert, template: str) -> tuple[bool, Optional[str]]:
        """
        发送通知
        返回: (是否成功, 错误信息)
        """
        pass

    def format_message(self, alert: Alert, template: str) -> str:
        """格式化消息模板"""
        if not template:
            template = self.get_default_template()

        # 替换变量
        replacements = {
            "{{alert_id}}": str(alert.id),
            "{{title}}": alert.title or "",
            "{{content}}": alert.content or "",
            "{{severity}}": alert.severity or "",
            "{{source}}": alert.source or "",
            "{{status}}": alert.status or "",
            "{{fired_at}}": alert.fired_at.isoformat() if alert.fired_at else "",
            "{{alert_key}}": alert.alert_key or "",
            "{{fire_count}}": str(alert.fire_count),
        }

        # 处理标签
        if alert.labels:
            for key, value in alert.labels.items():
                replacements[f"{{{{labels.{key}}}}}"] = str(value)

        # 处理指标
        if alert.metric_name:
            replacements["{{metric_name}}"] = alert.metric_name
        if alert.metric_value:
            if isinstance(alert.metric_value, dict):
                replacements["{{metric_value}}"] = str(alert.metric_value.get("value", ""))
            else:
                replacements["{{metric_value}}"] = str(alert.metric_value)

        message = template
        for key, value in replacements.items():
            message = message.replace(key, value)

        return message

    def get_default_template(self) -> str:
        """获取默认模板"""
        return """【{{severity.upper}}】{{title}}

来源: {{source}}
时间: {{fired_at}}
告警ID: {{alert_id}}

{{content}}
"""


class ChannelFactory:
    """渠道工厂"""

    _channels: Dict[str, type] = {}

    @classmethod
    def register(cls, channel_type: str, channel_class: type):
        cls._channels[channel_type] = channel_class

    @classmethod
    def get_channel(cls, channel_type: str, config: Dict[str, Any]) -> NotificationChannel:
        channel_class = cls._channels.get(channel_type)
        if not channel_class:
            raise ValueError(f"Unknown channel type: {channel_type}")
        return channel_class(config)

    @classmethod
    async def send_alert(cls, channel_type: str, config: Dict[str, Any], alert: Alert, template: str = None) -> tuple[bool, Optional[str]]:
        """快捷发送方法"""
        try:
            channel = cls.get_channel(channel_type, config)
            return await channel.send(alert, template)
        except Exception as e:
            logger.error("channel_send_error", channel_type=channel_type, error=str(e))
            return False, str(e)


# 注册内置渠道
from apps.notify.channels.dingtalk import DingTalkChannel
from apps.notify.channels.feishu import FeishuChannel
from apps.notify.channels.wecom import WeComChannel
from apps.notify.channels.email import EmailChannel
from apps.notify.channels.webhook import WebhookChannel
from apps.notify.channels.slack import SlackChannel

ChannelFactory.register("dingtalk", DingTalkChannel)
ChannelFactory.register("feishu", FeishuChannel)
ChannelFactory.register("wecom", WeComChannel)
ChannelFactory.register("email", EmailChannel)
ChannelFactory.register("webhook", WebhookChannel)
ChannelFactory.register("slack", SlackChannel)
