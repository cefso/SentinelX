"""
SentinelX - Zabbix 告警适配器
"""
from typing import Dict, Any, Optional
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class ZabbixAdapter(AlertAdapter):
    """Zabbix告警适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析Zabbix告警格式
        Zabbix通常通过webhook推送告警
        """
        # 检查是否为Zabbix格式
        if "host" not in raw_data and "event" not in raw_data:
            return None

        event = raw_data.get("event", {})
        severity_map = {
            "not_classified": "info",
            "info": "info",
            "warning": "medium",
            "average": "high",
            "high": "high",
            "disaster": "critical",
        }

        severity = severity_map.get(
            raw_data.get("severity", "high"),
            "medium"
        )

        return AlertCreate(
            alert_key=f"zabbix-{raw_data.get('event_id', raw_data.get('trigger_id', 'unknown'))}",
            source="zabbix",
            title=raw_data.get("trigger_name", "Zabbix Alert"),
            content=raw_data.get("trigger_description", ""),
            severity=severity,
            labels={
                "host": raw_data.get("host"),
                "ip": raw_data.get("ip"),
                "severity": raw_data.get("severity"),
            },
            annotations={
                "event_id": raw_data.get("event_id"),
                "trigger_id": raw_data.get("trigger_id"),
            },
            metric_name=raw_data.get("item_name"),
            metric_value={"value": raw_data.get("item_value")},
            raw_data=raw_data,
        )

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        return "host" in raw_data or "event" in raw_data
