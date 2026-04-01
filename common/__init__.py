"""
SentinelX - 公共共享模块
提供后端、Agent、工具脚本等共享的常量、类型定义和工具函数
"""

from common.constants import (
    AlertSeverity,
    AlertStatus,
    AlertSourceType,
    NotificationChannelType,
    RuleConditionOperator,
    SeverityLevel,
    SEVERITY_ORDER,
)
from common.types import (
    AlertLabels,
    AlertMetrics,
    AlertAnnotations,
    HealthStatus,
    HeartbeatPayload,
    MetricsPayload,
)
from common.utils import (
    generate_fingerprint,
    get_timestamp,
    parse_labels,
    truncate_string,
    mask_sensitive,
)

__all__ = [
    # Constants
    "AlertSeverity",
    "AlertStatus",
    "AlertSourceType",
    "NotificationChannelType",
    "RuleConditionOperator",
    "SeverityLevel",
    "SEVERITY_ORDER",
    # Types
    "AlertLabels",
    "AlertMetrics",
    "AlertAnnotations",
    "HealthStatus",
    "HeartbeatPayload",
    "MetricsPayload",
    # Utils
    "generate_fingerprint",
    "get_timestamp",
    "parse_labels",
    "truncate_string",
    "mask_sensitive",
]
