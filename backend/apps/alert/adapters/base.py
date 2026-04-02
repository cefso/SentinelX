"""
SentinelX - 告警适配器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from apps.alert.schemas import AlertCreate


class AlertAdapter(ABC):
    """告警适配器基类 - 策略模式"""

    def __init__(self):
        self.source_type = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析原始告警数据为标准AlertCreate格式
        返回None表示该数据不适用于此适配器
        """
        pass

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        """验证数据是否适用于此适配器"""
        return True

    def generate_fingerprint(self, alert_key: str, source: str, labels: Dict[str, Any]) -> str:
        """生成告警指纹"""
        import hashlib
        import json

        fp_data = {
            "source": source,
            "alert_key": alert_key,
            "labels": json.dumps(labels, sort_keys=True, default=str),
        }
        fp_json = json.dumps(fp_data, sort_keys=True, default=str)
        return hashlib.sha256(fp_json.encode()).hexdigest()[:16]


class PrometheusAdapter(AlertAdapter):
    """Prometheus/Alertmanager适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
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
            annotations=raw_data,
            raw_data=raw_data,
        )

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        return "appid" in raw_data or "dimension" in raw_data


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


class AdapterFactory:
    """适配器工厂"""

    _adapters = {
        "prometheus": PrometheusAdapter,
        "alertmanager": PrometheusAdapter,  # alertmanager使用prometheus适配器
        "zabbix": ZabbixAdapter,
        "aliyun": AlibabaCloudAdapter,
        "aliyun_cms": "AliyunCmsAdapter",  # 延迟导入
        "tencent": TencentCloudAdapter,
        "custom": CustomWebhookAdapter,
    }

    @classmethod
    def get_adapter(cls, source_type: str) -> AlertAdapter:
        """获取适配器"""
        adapter_class = cls._adapters.get(source_type.lower(), CustomWebhookAdapter)
        # 延迟导入处理
        if isinstance(adapter_class, str):
            from apps.alert.adapters.aliyun_cms import AliyunCmsAdapter
            adapter_class = AliyunCmsAdapter
        return adapter_class()

    @classmethod
    def auto_detect(cls, raw_data: Dict[str, Any]) -> AlertAdapter:
        """自动检测数据源类型"""
        # 按优先级检测
        if "aliyun_alert" in raw_data:
            return AlibabaCloudAdapter()
        if "appid" in raw_data or "dimension" in raw_data:
            return TencentCloudAdapter()
        if "host" in raw_data or "event" in raw_data:
            return ZabbixAdapter()
        if "alerts" in raw_data or ("labels" in raw_data and "annotations" in raw_data):
            return PrometheusAdapter()
        if "metric" in raw_data:
            return PrometheusMetricsAdapter()

        return CustomWebhookAdapter()
