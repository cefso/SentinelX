"""
阿里云云监控1.0适配器
支持 URL-encoded form data 格式
"""
from typing import Dict, Any, Optional
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class AliyunCmsAdapter(AlertAdapter):
    """阿里云云监控1.0适配器"""

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析阿里云云监控1.0告警格式
        阿里云云监控1.0发送的是 URL-encoded form data 格式:
        lastTime=5%E5%A4%A9&rawMetricName=CPUUtilization&expression=%24Value+%3E+75&...
        """
        # 检查是否为阿里云云监控1.0格式
        # 关键字段: lastTime, rawMetricName, alertName (而非 aliyun_alert)
        if "lastTime" not in raw_data and "rawMetricName" not in raw_data:
            return None

        # 解析字段映射
        last_time = raw_data.get("lastTime", "")
        raw_metric_name = raw_data.get("rawMetricName", "")
        expression = raw_data.get("expression", "")
        metric_name = raw_data.get("metricName", "")
        alert_name = raw_data.get("alertName", raw_data.get("alert_name", ""))
        alert_state = raw_data.get("alertState", raw_data.get("alert_state", ""))

        # 构建标题
        title = f"阿里云云监控: {alert_name or metric_name or raw_metric_name}"

        # 构建内容
        content_parts = []
        if last_time:
            content_parts.append(f"持续时间: {last_time}")
        if expression:
            content_parts.append(f"表达式: {expression}")
        if raw_metric_name:
            content_parts.append(f"原始指标: {raw_metric_name}")
        if metric_name:
            content_parts.append(f"指标名称: {metric_name}")
        content = "\n".join(content_parts) if content_parts else raw_data.get("message", str(raw_data))

        # 严重级别判断
        severity = self._determine_severity(raw_data)

        # 生成唯一告警键（不包含lastTime，避免同一告警因持续时间变化导致指纹不同）
        alert_key = f"aliyun_cms-{alert_name}-{raw_metric_name}"

        return AlertCreate(
            alert_key=alert_key,
            source="aliyun_cms",
            title=title,
            content=content,
            severity=severity,
            labels={
                "last_time": last_time,
                "raw_metric_name": raw_metric_name,
                "expression": expression,
                "metric_name": metric_name,
            },
            annotations={
                "alert_name": alert_name,
                "alert_state": alert_state,
                "raw_data": raw_data,  # 保留原始数据用于追踪
            },
            metric_name=metric_name or raw_metric_name,
            metric_value={"expression": expression},
            raw_data=raw_data,
        )

    def _determine_severity(self, raw_data: Dict[str, Any]) -> str:
        """根据告警状态和数据判断严重级别"""
        alert_state = raw_data.get("alertState", raw_data.get("alert_state", ""))
        severity = raw_data.get("severity", "").upper()

        # 已恢复的告警降为 info
        if alert_state == "OK" or alert_state == "RESOLVED":
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

        # 默认根据表达式判断
        expression = raw_data.get("expression", "")
        if ">" in expression or "<" in expression:
            return "high"  # 有阈值条件的默认为高级别

        return "medium"

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        """检查是否为阿里云云监控1.0格式"""
        return "lastTime" in raw_data or "rawMetricName" in raw_data
