"""
SentinelX - Alert 共享工具函数
"""
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from apps.alert.models import Alert

from apps.alert.schemas import AlertResponse


def build_alert_response(alert: "Alert", source_name: Optional[str] = None) -> AlertResponse:
    """将 Alert 模型转换为响应，附带告警源显示名称"""
    response = AlertResponse.model_validate(alert)
    if source_name:
        return response.model_copy(update={"source_name": source_name})
    return response


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
