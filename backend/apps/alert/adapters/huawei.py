"""
SentinelX - 华为云 SMN 告警适配器
解析华为云云监控通过 SMN 推送的 CES 告警
"""
import re
from typing import Dict, Any, Optional
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class HuaweiAdapter(AlertAdapter):
    """华为云云监控告警适配器（SMN格式）"""

    SEVERITY_MAP = {
        "紧急": "critical",
        "重要": "high",
        "次要": "medium",
    }

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        if not self.validate(raw_data):
            return None

        subject = raw_data.get("subject", "")
        message = raw_data.get("message", "")

        # 从 subject 提取告警级别和资源描述
        severity = "medium"
        level_match = re.search(r"\[(紧急|重要|次要)告警\]", subject)
        if level_match:
            severity = self.SEVERITY_MAP.get(level_match.group(1), "medium")

        # title：去掉前缀标签
        title = re.sub(r"^\[华为云\]\[.+?告警\]云监控通知[：:]", "", subject).strip()
        title = title.rstrip("。")

        # 从 message 提取各字段
        fields = self._extract_fields(message)

        # alert_key：告警规则 + 资源ID前8位
        rule = fields.get("rule", "unknown")
        resource_id = fields.get("resource_id", "unknown")
        short_id = resource_id[:8] if len(resource_id) >= 8 else resource_id
        alert_key = f"huawei-{rule}-{short_id}"

        # labels
        labels: Dict[str, Any] = {}
        if fields.get("ip"):
            labels["ip"] = fields["ip"]
        if fields.get("resource_id"):
            labels["resource_id"] = fields["resource_id"]
        if fields.get("spec"):
            labels["spec"] = fields["spec"]
        if fields.get("region"):
            labels["region"] = fields["region"]

        # annotations
        annotations: Dict[str, Any] = {}
        if fields.get("rule"):
            annotations["rule"] = fields["rule"]
        if fields.get("serial_number"):
            annotations["serial_number"] = fields["serial_number"]
        if fields.get("alert_type"):
            annotations["alert_type"] = fields["alert_type"]
        if fields.get("threshold"):
            annotations["threshold"] = fields["threshold"]
        if fields.get("trigger_time"):
            annotations["trigger_time"] = fields["trigger_time"]
        if raw_data.get("topic_urn"):
            annotations["topic_urn"] = raw_data["topic_urn"]

        return AlertCreate(
            alert_key=alert_key,
            source="huawei",
            title=title,
            content=message,
            severity=severity,
            labels=labels,
            annotations=annotations,
            metric_name=fields.get("metric_name"),
            metric_value=fields.get("metric_value"),
            raw_data=raw_data,
        )

    def _extract_fields(self, message: str) -> Dict[str, str]:
        """从 message 文本中提取各字段"""
        fields: Dict[str, str] = {}

        # 区域：第一个方括号
        region_match = re.search(r"\[(.+?)\]", message)
        if region_match:
            fields["region"] = region_match.group(1)

        # 私网IP
        ip_match = re.search(r"私网IP[：:]([0-9.]+)", message)
        if ip_match:
            fields["ip"] = ip_match.group(1)

        # 规格
        spec_match = re.search(r"规格[：:]([^\s,，)]+)", message)
        if spec_match:
            fields["spec"] = spec_match.group(1)

        # 资源ID
        rid_match = re.search(r"资源ID[：:]([a-f0-9-]+)", message)
        if rid_match:
            fields["resource_id"] = rid_match.group(1)

        # 指标名："的XXX连续"
        metric_match = re.search(r"的(.+?)连续", message)
        if metric_match:
            fields["metric_name"] = metric_match.group(1)

        # 当前数据
        value_match = re.search(r"当前数据[：:]\s*([\d.]+\s*%)", message)
        if value_match:
            fields["metric_value"] = value_match.group(1)

        # 阈值："原始值 >= 0 %"
        threshold_match = re.search(r"原始值\s*(>=?\s*\d+[\d.]*)\s*%", message)
        if threshold_match:
            fields["threshold"] = f"原始值 {threshold_match.group(1)} %"

        # 触发时间
        time_match = re.search(r"于(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})", message)
        if time_match:
            fields["trigger_time"] = time_match.group(1)

        # 告警流水号
        serial_match = re.search(r"告警流水号[：:]([A-Za-z0-9]+)", message)
        if serial_match:
            fields["serial_number"] = serial_match.group(1)

        # 告警规则
        rule_match = re.search(r"告警规则[：:]([A-Za-z0-9-]+)", message)
        if rule_match:
            fields["rule"] = rule_match.group(1)

        # 告警通知类型
        type_match = re.search(r"告警通知类型[：:](\S+)", message)
        if type_match:
            fields["alert_type"] = type_match.group(1)

        return fields

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        return (
            raw_data.get("type") == "Notification"
            and bool(raw_data.get("subject"))
            and bool(raw_data.get("message"))
        )
