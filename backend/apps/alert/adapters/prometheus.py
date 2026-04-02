"""
SentinelX - Prometheus/Alertmanager 告警适配器
"""
from typing import Dict, Any, Optional, List
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class PrometheusAdapter(AlertAdapter):
    """Prometheus/Alertmanager适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate | List[AlertCreate]]:
        """
        解析Prometheus告警格式
        支持两种格式:
        1. Alertmanager webhook格式
        2. Prometheus alerting rule格式
        """
        # Alertmanager webhook格式
        if "alerts" in raw_data:
            alerts = []
            for alert in raw_data.get("alerts", []):
                parsed = await self._parse_alertmanager_alert(alert, tenant_id)
                if parsed:
                    alerts.append(parsed)
            return alerts  # 返回列表

        # 单个告警格式
        if "labels" in raw_data:
            return await self._parse_alertmanager_alert(raw_data, tenant_id)

        return None

    async def _parse_alertmanager_alert(self, alert: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """解析Alertmanager告警"""
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        # 状态: firing/resolved
        status = alert.get("status", "firing")
        if status == "resolved":
            severity = "info"  # 已恢复的告警降为info
        else:
            severity = labels.get("severity", "critical")

        return AlertCreate(
            alert_key=labels.get("alertname", "unknown"),
            source="alertmanager",
            title=annotations.get("summary", labels.get("alertname", "Unknown Alert")),
            content=annotations.get("description", ""),
            severity=severity,
            labels=labels,
            annotations=annotations,
            metric_name=labels.get("metric_name"),
            metric_value={"value": annotations.get("value")},
            raw_data=alert,
        )

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        """检查是否为Alertmanager格式"""
        return "alerts" in raw_data or "labels" in raw_data


class PrometheusMetricsAdapter(AlertAdapter):
    """Prometheus metrics alerting适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析Prometheus metrics告警
        这种格式来自Prometheus的 alerting rule push
        """
        if "metric" not in raw_data:
            return None

        metric = raw_data.get("metric", {})
        value = raw_data.get("value")
        alert_name = metric.get("alertname", metric.get("__name__", "unknown"))

        # 严重级别从标签获取
        severity = metric.get("severity", "critical")

        return AlertCreate(
            alert_key=alert_name,
            source="prometheus",
            title=f"Prometheus告警: {alert_name}",
            content=f"指标 {metric.get('__name__')} 触发告警阈值",
            severity=severity,
            labels=metric,
            annotations=raw_data.get("annotations", {}),
            metric_name=metric.get("__name__"),
            metric_value={"value": value},
            raw_data=raw_data,
        )

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        return "metric" in raw_data and "value" in raw_data
