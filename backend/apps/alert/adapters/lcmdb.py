"""
SentinelX - 绿城CMDB告警适配器
解析 markdown 格式的 webhook，text 字段为换行分隔的 key：value 对
"""
import re
from typing import Dict, Any, Optional, List
from .base import AlertAdapter
from apps.alert.schemas import AlertCreate


class LcmdbAdapter(AlertAdapter):
    """绿城CMDB告警适配器"""

    SEVERITY_MAP = {
        "严重": "critical",
        "警告": "high",
        "提示": "medium",
        "信息": "info",
        "恢复": "info",
    }

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        if not self.validate(raw_data):
            return None

        markdown = raw_data["markdown"]
        text = markdown.get("text", "")

        # 解析 key：value 对（中文冒号）
        fields: Dict[str, str] = {}
        for line in text.split("\n"):
            match = re.match(r"^(.+?)：(.+)$", line.strip())
            if match:
                fields[match.group(1).strip()] = match.group(2).strip()

        if not fields:
            return None

        # severity：去HTML标签后映射
        raw_status = re.sub(r"<[^>]+>", "", fields.get("当前状态", ""))
        severity = self.SEVERITY_MAP.get(raw_status, "medium")
        is_recovery = raw_status == "恢复"

        # 告警对象 → title
        title = fields.get("告警对象", "CMDB Alert")

        # 从告警对象提取简称用于 alert_key，如 "企业知识库-测试环境 的 [磁盘:Disk]" → "磁盘"
        short_name = ""
        bracket_match = re.search(r"\[.+?:(.+?)\]", title)
        if bracket_match:
            short_name = bracket_match.group(1)
        else:
            short_name = title[:20]

        device_id = fields.get("设备ID", "unknown")
        alert_key = f"lcmdb-{device_id}-{short_name}"

        # 当前指标：磁盘使用率=[5.89%] → metric_name + metric_value
        metric_name = None
        metric_value = None
        current = fields.get("当前", "")
        metric_match = re.match(r"(.+?)=\[(.+?)\]", current)
        if metric_match:
            metric_name = metric_match.group(1).strip()
            metric_value = metric_match.group(2).strip()

        # 阈值：去方括号
        threshold = fields.get("阈值", "")
        threshold = threshold.strip("[]")

        # annotations
        annotations: Dict[str, Any] = {}
        if threshold:
            annotations["threshold"] = threshold
        if fields.get("持续时间"):
            annotations["duration"] = fields["持续时间"]
        if fields.get("开始时间"):
            annotations["start_time"] = fields["开始时间"]
        if fields.get("告警编号"):
            annotations["alert_id"] = fields["告警编号"]
        if is_recovery:
            annotations["alert_state"] = "OK"

        # labels
        labels: Dict[str, Any] = {}
        if fields.get("设备ID"):
            labels["device_id"] = fields["设备ID"]
        if fields.get("IP地址"):
            labels["ip"] = fields["IP地址"]
        if fields.get("设备类型"):
            labels["device_type"] = fields["设备类型"]

        # 未识别的字段兜底存入 annotations
        known_keys = {"告警编号", "告警对象", "设备ID", "当前", "阈值", "当前状态", "IP地址", "持续时间", "设备类型", "开始时间"}
        for k, v in fields.items():
            if k not in known_keys:
                annotations[k] = v

        return AlertCreate(
            alert_key=alert_key,
            source="lcmdb",
            title=title,
            content=text,
            severity=severity,
            labels=labels,
            annotations=annotations,
            metric_name=metric_name,
            metric_value=metric_value,
            raw_data=raw_data,
        )

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        markdown = raw_data.get("markdown")
        if not markdown or not isinstance(markdown, dict):
            return False
        return bool(markdown.get("text"))
