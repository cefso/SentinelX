"""
SentinelX - 绿城CMDB告警适配器
解析 markdown 格式的 webhook，text 字段为换行分隔的 key：value 对
支持告警和恢复两种模板格式
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
        "正常": "info",
    }

    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        if not self.validate(raw_data):
            return None

        markdown = raw_data["markdown"]
        text = markdown.get("text", "")

        # 处理转义的换行符（\n 变成实际换行）
        text = text.replace("\\n", "\n")

        # 全局去除 HTML 标签（如 <font color='green'>正常</font>）
        text = re.sub(r"<[^>]+>", "", text)

        # 解析 key：value 对（中文冒号）+ 收集独立描述行
        fields: Dict[str, str] = {}
        desc_lines: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            match = re.match(r"^(.+?)：(.+)$", stripped)
            if match:
                fields[match.group(1).strip()] = match.group(2).strip()
            else:
                desc_lines.append(stripped)

        if not fields and not desc_lines:
            return None

        # severity：兼容 当前状态 / 状态
        raw_status = fields.get("当前状态") or fields.get("状态") or ""
        severity = self.SEVERITY_MAP.get(raw_status, "medium")
        is_recovery = raw_status in ("恢复", "正常") or markdown.get("title") == "恢复通知"

        # 告警对象 / 恢复对象 → title
        title = fields.get("告警对象") or fields.get("恢复对象") or "CMDB Alert"

        # 从告警对象提取简称用于 alert_key，如 "企业知识库-测试环境 的 [磁盘:Disk]" → "磁盘"
        short_name = ""
        bracket_match = re.search(r"\[.+?:(.+?)\]", title)
        if bracket_match:
            short_name = bracket_match.group(1)
        else:
            short_name = title[:20]

        ip = fields.get("IP地址", "unknown")
        alert_key = f"lcmdb-{ip}-{short_name}"

        # 当前指标：从独立描述行提取，如 "当前:5分平均值=[22.95];"
        metric_name = None
        metric_value = None
        for line in desc_lines:
            metric_match = re.match(r"当前[:：](.+?)=\[(.+?)\]", line)
            if metric_match:
                metric_name = metric_match.group(1).strip()
                metric_value = metric_match.group(2).strip()
                break

        # 阈值：从独立描述行提取，如 "阈值:[5分平均值 > 20]"
        threshold = ""
        for line in desc_lines:
            threshold_match = re.match(r"阈值[:：]\[(.+?)\]", line)
            if threshold_match:
                threshold = threshold_match.group(1).strip()
                break

        # annotations
        annotations: Dict[str, Any] = {}
        if threshold:
            annotations["threshold"] = threshold
        if fields.get("持续时间"):
            annotations["duration"] = fields["持续时间"]
        start_time = fields.get("开始时间") or fields.get("恢复时间")
        if start_time:
            annotations["start_time"] = start_time
        alert_id = fields.get("告警编号") or fields.get("恢复编号")
        if alert_id:
            annotations["alert_id"] = alert_id
        if is_recovery:
            annotations["alert_state"] = "OK"

        # labels（只放稳定标识，不参与指纹变化的字段）
        labels: Dict[str, Any] = {}
        if fields.get("IP地址"):
            labels["ip"] = fields["IP地址"]
        if fields.get("设备类型"):
            labels["device_type"] = fields["设备类型"]

        # device_id 放入 annotations（同一台机器的设备ID可能不同，不参与指纹）
        if fields.get("设备ID"):
            annotations["device_id"] = fields["设备ID"]

        # 未识别的字段兜底存入 annotations
        known_keys = {"告警编号", "恢复编号", "告警对象", "恢复对象", "设备ID", "当前状态", "状态", "IP地址", "持续时间", "设备类型", "开始时间", "恢复时间"}
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
