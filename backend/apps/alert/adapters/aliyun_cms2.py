"""
阿里云云监控2.0适配器
支持 JSON 格式
"""
from typing import Dict, Any, Optional
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class AliyunCms2Adapter(AlertAdapter):
    """阿里云云监控2.0适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析阿里云云监控2.0告警格式
        阿里云云监控2.0发送的是 JSON 格式:
        {"alertName": "...", "metricName": "...", "namespace": "...", ...}
        """
        # 检查是否为阿里云云监控2.0格式
        # 关键字段: alertName, metricName, namespace (而非 lastTime, rawMetricName)
        if "alertName" not in raw_data and "metricName" not in raw_data:
            return None

        alert_name = raw_data.get("alertName", raw_data.get("alert_name", ""))
        metric_name = raw_data.get("metricName", raw_data.get("metric_name", ""))
        namespace = raw_data.get("namespace", "")
        condition = raw_data.get("condition", "")
        state = raw_data.get("state", raw_data.get("status", ""))

        # 构建标题
        title = f"阿里云云监控2.0: {alert_name or metric_name}"

        # 构建内容
        content_parts = []
        if metric_name:
            content_parts.append(f"指标: {metric_name}")
        if namespace:
            content_parts.append(f"命名空间: {namespace}")
        if condition:
            content_parts.append(f"条件: {condition}")
        if state:
            content_parts.append(f"状态: {state}")
        content = "\n".join(content_parts) if content_parts else raw_data.get("message", str(raw_data))

        # 严重级别判断
        severity = self._determine_severity(raw_data)

        # 生成唯一告警键
        alert_key = f"aliyun_cms2-{alert_name}-{metric_name}-{namespace}"

        return AlertCreate(
            alert_key=alert_key,
            source="aliyun_cms2",
            title=title,
            content=content,
            severity=severity,
            labels={
                "metric_name": metric_name,
                "namespace": namespace,
                "condition": condition,
            },
            annotations={
                "alert_name": alert_name,
                "state": state,
                "raw_data": raw_data,
            },
            metric_name=metric_name,
            metric_value={"condition": condition},
            raw_data=raw_data,
        )

    def _determine_severity(self, raw_data: Dict[str, Any]) -> str:
        """根据告警状态和数据判断严重级别"""
        severity = raw_data.get("severity", "").upper()
        state = raw_data.get("state", raw_data.get("status", "")).upper()

        # 已恢复的告警降为 info
        if state == "OK" or state == "RESOLVED":
            return "info"

        # 级别映射
        severity_map = {
            "CRITICAL": "critical",
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
            "INFO": "info",
        }

        if severity in severity_map:
            return severity_map[severity]

        # 默认根据条件判断
        condition = raw_data.get("condition", "")
        if ">" in condition or "<" in condition or ">=" in condition or "<=" in condition:
            return "high"

        return "medium"

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        """检查是否为阿里云云监控2.0格式"""
        return "alertName" in raw_data or ("metricName" in raw_data and "namespace" in raw_data)
