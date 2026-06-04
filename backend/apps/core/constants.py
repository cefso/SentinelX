"""
SentinelX - 公共常量定义
告警级别、状态、来源类型、通知渠道类型等跨模块共享常量
"""

# ============ 告警级别 ============
class AlertSeverity:
    """告警级别"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    ALL = (CRITICAL, HIGH, MEDIUM, LOW, INFO)

    # 级别到数值的映射（用于排序和比较）
    _LEVEL_MAP = {
        CRITICAL: 0,
        HIGH: 1,
        MEDIUM: 2,
        LOW: 3,
        INFO: 4,
    }

    @classmethod
    def get_priority(cls, severity: str) -> int:
        """获取级别优先级，数值越小优先级越高"""
        return cls._LEVEL_MAP.get(severity, 999)

    @classmethod
    def is_valid(cls, severity: str) -> bool:
        """检查是否是有效的告警级别"""
        return severity in cls.ALL

    @classmethod
    def max_severity(cls, sev1: str, sev2: str) -> str:
        """返回两个级别中较高的一个"""
        p1, p2 = cls.get_priority(sev1), cls.get_priority(sev2)
        return sev1 if p1 <= p2 else sev2


# ============ 告警级别数值映射 (用于排序) ============
SeverityLevel = dict[str, int]
SEVERITY_ORDER: list[str] = [
    AlertSeverity.CRITICAL,
    AlertSeverity.HIGH,
    AlertSeverity.MEDIUM,
    AlertSeverity.LOW,
    AlertSeverity.INFO,
]


# ============ 告警状态 ============
class AlertStatus:
    """告警状态"""
    FIRING = "firing"          # 告警中
    RESOLVED = "resolved"      # 已恢复
    ACKNOWLEDGED = "acknowledged"  # 已确认
    SILENCED = "silenced"      # 已静默

    ALL = (FIRING, RESOLVED, ACKNOWLEDGED, SILENCED)

    @classmethod
    def is_valid(cls, status: str) -> bool:
        return status in cls.ALL


# ============ 告警来源类型 ============
class AlertSourceType:
    """告警来源类型"""
    PROMETHEUS = "prometheus"
    ALERTMANAGER = "alertmanager"
    ALIYUN = "aliyun"
    ALIYUN_CMS = "aliyun_cms"   # 阿里云云监控1.0
    ALIYUN_CMS2 = "aliyun_cms2"  # 阿里云云监控2.0
    TENCENT = "tencent"
    HUAWEI = "huawei"
    ZABBIX = "zabbix"
    GRAFANA = "grafana"
    CUSTOM = "custom"          # 自定义 Webhook
    AGENT = "agent"            # Agent 上报

    ALL = (
        PROMETHEUS,
        ALERTMANAGER,
        ALIYUN,
        ALIYUN_CMS,
        ALIYUN_CMS2,
        TENCENT,
        HUAWEI,
        ZABBIX,
        GRAFANA,
        CUSTOM,
        AGENT,
    )

    # 来源类型对应的接收路径
    WEBHOOK_PATHS: dict[str, str] = {
        PROMETHEUS: "/api/v1/webhooks/{tenant}/prometheus/{client_id}",
        ALERTMANAGER: "/api/v1/webhooks/{tenant}/alertmanager/{client_id}",
        ALIYUN: "/api/v1/webhooks/{tenant}/aliyun/{client_id}",
        ALIYUN_CMS: "/api/v1/webhooks/{tenant}/aliyun_cms/{client_id}",
        ALIYUN_CMS2: "/api/v1/webhooks/{tenant}/aliyun_cms2/{client_id}",
        TENCENT: "/api/v1/webhooks/{tenant}/tencent/{client_id}",
        HUAWEI: "/api/v1/webhooks/{tenant}/huawei/{client_id}",
        ZABBIX: "/api/v1/webhooks/{tenant}/zabbix/{client_id}",
        GRAFANA: "/api/v1/webhooks/{tenant}/grafana/{client_id}",
        CUSTOM: "/api/v1/webhooks/{tenant}/custom/{client_id}",
    }

    @classmethod
    def is_valid(cls, source_type: str) -> bool:
        return source_type in cls.ALL


# ============ 通知渠道类型 ============
class NotificationChannelType:
    """通知渠道类型"""
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    WECOM = "wecom"            # 企业微信
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    LARK = "lark"

    ALL = (DINGTALK, FEISHU, WECOM, EMAIL, WEBHOOK, SLACK, LARK)

    @classmethod
    def is_valid(cls, channel_type: str) -> bool:
        return channel_type in cls.ALL


# ============ 规则条件操作符 ============
class RuleConditionOperator:
    """规则条件操作符"""
    EQ = "eq"                  # 等于
    NE = "ne"                  # 不等于
    GT = "gt"                  # 大于
    GTE = "gte"                # 大于等于
    LT = "lt"                  # 小于
    LTE = "lte"                # 小于等于
    IN = "in"                  # 包含
    NOT_IN = "not_in"          # 不包含
    CONTAINS = "contains"       # 字符串包含
    NOT_CONTAINS = "not_contains"  # 字符串不包含
    REGEX = "regex"            # 正则匹配
    NOT_REGEX = "not_regex"     # 正则不匹配
    EXISTS = "exists"           # 字段存在
    NOT_EXISTS = "not_exists"   # 字段不存在

    ALL = (
        EQ, NE, GT, GTE, LT, LTE,
        IN, NOT_IN,
        CONTAINS, NOT_CONTAINS,
        REGEX, NOT_REGEX,
        EXISTS, NOT_EXISTS,
    )

    # 支持数值的操作符
    NUMERIC_OPS = (GT, GTE, LT, LTE)

    # 支持列表的操作符
    LIST_OPS = (IN, NOT_IN)

    # 支持字符串的操作符
    STRING_OPS = (CONTAINS, NOT_CONTAINS, REGEX, NOT_REGEX)

    @classmethod
    def is_valid(cls, op: str) -> bool:
        return op in cls.ALL


# ============ 追踪状态 ============
class TraceStatus:
    """告警追踪最终状态"""
    SENT = "sent"
    SUPPRESSED = "suppressed"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    PENDING = "pending"


# ============ 规则匹配模式 ============
class RuleMatchMode:
    """规则条件匹配模式"""
    AND = "and"
    OR = "or"
    ALL = (AND, OR)


# ============ 用户角色代码 ============
class RoleCode:
    """系统预置角色代码"""
    SUPER_ADMIN = "super_admin"    # 超级管理员
    TENANT_ADMIN = "tenant_admin"  # 租户管理员
    OPERATOR = "operator"           # 运维人员
    VIEWER = "viewer"              # 只读用户


# ============ API Key 前缀 ============
class APIKeyPrefix:
    """API Key 前缀"""
    WEBHOOK = "sxw"     # Webhook API Key
    AGENT = "sxa"       # Agent API Key
    SERVICE = "sxs"     # 服务间调用 Key

    @classmethod
    def detect(cls, api_key: str) -> str | None:
        """从 API Key 内容检测类型"""
        if api_key.startswith("sxw_v1_"):
            return "webhook"
        if api_key.startswith("sxa_v1_"):
            return "agent"
        if api_key.startswith("sxs_v1_"):
            return "service"
        return None
