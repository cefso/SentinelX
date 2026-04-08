"""
SentinelX - 腾讯云告警适配器
"""
from typing import Dict, Any, Optional
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class TencentCloudAdapter(AlertAdapter):
    """腾讯云告警适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """解析腾讯云告警格式"""
        # 腾讯云告警通知格式
        if "appid" not in raw_data and "dimension" not in raw_data:
            return None

        severity_map = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
            "FIXED": "info",
        }

        return AlertCreate(
            alert_key=raw_data.get("notice_id", raw_data.get("topic_id", "unknown")),
            source="tencent",
            title=raw_data.get("policy_name", "Tencent Cloud Alert"),
            content=raw_data.get("message", ""),
            severity=severity_map.get(raw_data.get("severity", "HIGH"), "medium"),
            labels={
                "appid": raw_data.get("appid"),
                "region": raw_data.get("region"),
            },
            annotations=raw_data.get("annotations", {}),
            raw_data=raw_data,
        )

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        return "appid" in raw_data or "dimension" in raw_data
