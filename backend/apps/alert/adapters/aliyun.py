"""
SentinelX - 阿里云告警适配器
"""
from typing import Dict, Any, Optional
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class AlibabaCloudAdapter(AlertAdapter):
    """阿里云告警适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析阿里云告警格式
        阿里云监控通过webhook推送告警
        """
        if "aliyun_alert" not in raw_data:
            return None

        alert = raw_data.get("aliyun_alert", {})
        severity_map = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
            "INFO": "info",
        }

        return AlertCreate(
            alert_key=alert.get("alert_id", alert.get("alert_name", "unknown")),
            source="aliyun",
            title=alert.get("alert_name", "Alibaba Cloud Alert"),
            content=alert.get("alert_description", ""),
            severity=severity_map.get(alert.get("severity", "HIGH"), "medium"),
            labels={
                "region": alert.get("region"),
                "resource_group": alert.get("resource_group_id"),
                "product": alert.get("product"),
            },
            annotations={
                "alert_id": alert.get("alert_id"),
                "region": alert.get("region"),
            },
            raw_data=raw_data,
        )

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        return "aliyun_alert" in raw_data
