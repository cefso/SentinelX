"""
SentinelX - Alert 共享工具函数
"""
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from apps.alert.models import Alert

from apps.alert.schemas import AlertResponse


def extract_instance_from_title(title: str) -> Optional[str]:
    """从标题提取实例名，仅匹配明确格式，避免把整条标题当实例。

    - lcmdb：「主机/应用 的 [类型:对象]」→ 取「的」前名称
    - 常见：「host xxx」「实例 xxx」「主机: xxx」
    """
    if not title:
        return None
    match = re.search(r"^(.+?)\s*的\s*\[", title)
    if match:
        name = match.group(1).strip()
        if name and len(name) <= 80:
            return name
    match = re.search(r"(?:^|\s)(?:host|主机|实例)[:：\s]+([^\s,;，；]+)", title, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        if name:
            return name
    return None


def build_alert_response(
    alert: "Alert",
    source_name: Optional[str] = None,
    aggregate_group_count: Optional[int] = None,
) -> AlertResponse:
    """将 Alert 模型转换为响应，附带告警源显示名称"""
    data = AlertResponse.model_validate(alert).model_dump()
    if source_name:
        data["source_name"] = source_name
    if aggregate_group_count is not None:
        data["aggregate_group_count"] = aggregate_group_count
    return AlertResponse(**data)


def alert_to_dict(alert: "Alert") -> dict:
    """将 Alert 模型转换为字典，用于规则引擎评估"""
    return {
        # 基础字段
        "id": alert.id,
        "tenant_id": alert.tenant_id,
        "alert_key": alert.alert_key,
        "fingerprint": alert.fingerprint,
        "title": alert.title,
        "content": alert.content,
        "severity": alert.severity,
        "status": alert.status,
        "source": alert.source,
        "source_id": alert.source_id,
        # 云产品字段
        "namespace": alert.namespace,
        "instance_id": alert.instance_id,
        "instance_name": alert.instance_name,
        # 指标字段
        "metric_name": alert.metric_name,
        "metric_value": alert.metric_value,
        # 标签/注解/原始数据
        "labels": alert.labels or {},
        "annotations": alert.annotations or {},
        "raw_data": alert.raw_data or {},
        # 统计字段
        "fire_count": alert.fire_count,
        "repeat_count": alert.repeat_count,
        "escalation_count": alert.escalation_count,
        # 时间字段
        "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
        # 追踪字段
        "trace_id": alert.trace_id,
    }
