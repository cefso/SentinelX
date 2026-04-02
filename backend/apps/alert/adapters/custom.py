"""
SentinelX - 自定义 Webhook 告警适配器
"""
from typing import Dict, Any, Optional
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class CustomWebhookAdapter(AlertAdapter):
    """自定义Webhook适配器 - 通用JSON格式"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析自定义格式告警
        支持灵活配置的JSON格式
        """
        # 尝试识别通用字段
        title = (
            raw_data.get("title")
            or raw_data.get("alert_title")
            or raw_data.get("name")
            or raw_data.get("msg")
            or "Custom Alert"
        )

        content = (
            raw_data.get("content")
            or raw_data.get("description")
            or raw_data.get("message")
            or raw_data.get("body")
            or ""
        )

        severity = (
            raw_data.get("severity")
            or raw_data.get("level")
            or raw_data.get("priority")
            or "medium"
        )

        # 标准化严重级别
        severity = severity.lower()
        severity_map = {
            "critical": "critical",
            "fatal": "critical",
            "high": "high",
            "error": "high",
            "medium": "medium",
            "warning": "medium",
            "low": "low",
            "info": "info",
        }
        severity = severity_map.get(severity, "medium")

        return AlertCreate(
            alert_key=raw_data.get("id") or raw_data.get("alert_key") or title,
            source=raw_data.get("source", "custom"),
            title=title,
            content=str(content),
            severity=severity,
            labels=raw_data.get("labels", raw_data.get("tags", {})),
            annotations=raw_data.get("annotations", {}),
            metric_name=raw_data.get("metric_name") or raw_data.get("metric"),
            metric_value=raw_data.get("metric_value") or raw_data.get("value"),
            raw_data=raw_data,
        )
