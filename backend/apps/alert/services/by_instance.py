"""
实例维度告警聚合：实例识别、类型分类、分组统计。
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.alert.models import Alert, AlertSource
from apps.alert.schemas import AlertResponse
from apps.alert.services.alert_utils import build_alert_response

UNKNOWN_INSTANCE_KEY = "__unknown__"

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

# 按优先级匹配；首个命中即返回。
# 短/易误伤 token 使用词边界或前后缀形态，避免 amount→mount、program→ram、method→net。
TYPE_RULES: List[Tuple[str, str, List[str]]] = [
    ("cpu", "CPU", [r"cpu", r"processor", r"处理器"]),
    (
        "memory",
        "内存",
        [r"\bmem(?:ory)?\b", r"memory_", r"_memory", r"meminfo", r"mem_", r"内存", r"\bram\b"],
    ),
    (
        "disk",
        "磁盘",
        [r"disk", r"partition", r"\bmount\b", r"mount_", r"mountpoint", r"磁盘", r"存储", r"filesystem"],
    ),
    (
        "process",
        "进程",
        [r"\bprocess(?:es)?\b", r"process_", r"_process", r"进程", r"\.jar\b", r"\bjar\b", r"\bjava\b", r"java_"],
    ),
    (
        "network",
        "网络",
        [r"network", r"bandwidth", r"\bnet\b", r"net_", r"_net\b", r"net\.", r"netdev", r"网卡", r"网络", r"流量", r"\beth\d*\b"],
    ),
]

SCAN_WINDOW_DAYS = 90
MAX_SCAN = 20000


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_instance_from_title(title: str) -> Optional[str]:
    """从标题提取实例名，仅匹配明确格式，避免把整条标题当实例。

    - lcmdb：「主机/应用 的 [类型:对象]」
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


def extract_instance(alert: Alert) -> Dict[str, Optional[str]]:
    """多字段兜底识别实例。instance_key 用于聚合，instance_name 用于展示。

    优先级：instance_name → instance_id → labels.host → labels.instance
            → 标题「xx 的 [..]」首段（lcmdb）→ labels.ip → 未识别
    lcmdb 通常无 instance_name，但标题首段比 IP 更适合作为实例名。
    """
    labels = alert.labels or {}
    ip = _clean(labels.get("ip"))
    instance_name = _clean(alert.instance_name)
    instance_id = _clean(alert.instance_id)
    host = _clean(labels.get("host"))
    instance_label = _clean(labels.get("instance"))
    title_name = extract_instance_from_title(alert.title or "")

    key = (
        instance_name
        or instance_id
        or host
        or instance_label
        or title_name
        or ip
        or UNKNOWN_INSTANCE_KEY
    )

    if key == UNKNOWN_INSTANCE_KEY:
        shown_name: Optional[str] = None
    else:
        # 展示名优先友好名称；key 为 IP 时仍可用 title 名
        shown_name = instance_name or title_name or instance_id or host or instance_label or ip

    return {
        "instance_key": key,
        "instance_name": shown_name,
        "instance_id": instance_id,
        "ip": ip,
    }


def classify_alert_type(alert: Alert) -> Tuple[str, str]:
    """关键词映射告警类型，返回 (type_code, type_label)。"""
    labels = alert.labels or {}
    parts = [
        alert.metric_name or "",
        alert.alert_key or "",
        alert.title or "",
    ]
    for label_key in ("alertname", "metric_name", "trigger_name"):
        if labels.get(label_key):
            parts.append(str(labels[label_key]))
    text = " ".join(parts).lower()

    for code, label, patterns in TYPE_RULES:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return code, label
    return "other", "其他"


def max_severity(severities: Iterable[str]) -> Optional[str]:
    best: Optional[str] = None
    best_rank = len(SEVERITY_ORDER)
    for severity in severities:
        rank = SEVERITY_ORDER.get(severity, len(SEVERITY_ORDER))
        if rank < best_rank:
            best = severity
            best_rank = rank
    return best


def group_alerts_by_instance(
    alerts: List[Alert],
    source_names: Optional[Dict[int, str]] = None,
) -> List[Dict[str, Any]]:
    """将告警列表聚合为实例卡片结构（未排序、未分页）。"""
    source_names = source_names or {}
    instances: Dict[str, Dict[str, Any]] = {}

    for alert in alerts:
        info = extract_instance(alert)
        key = info["instance_key"]
        alert_type, type_label = classify_alert_type(alert)

        bucket = instances.get(key)
        if bucket is None:
            bucket = {
                "instance_key": key,
                "instance_name": info["instance_name"],
                "instance_id": info["instance_id"],
                "ip": info["ip"],
                "sources": set(),
                "alert_count": 0,
                "firing_count": 0,
                "severities": [],
                "last_fired_at": None,
                "types": {},
            }
            instances[key] = bucket

        if info["instance_name"] and not bucket["instance_name"]:
            bucket["instance_name"] = info["instance_name"]
        if info["ip"] and not bucket["ip"]:
            bucket["ip"] = info["ip"]
        if info["instance_id"] and not bucket["instance_id"]:
            bucket["instance_id"] = info["instance_id"]

        source_label = source_names.get(alert.source_id) if alert.source_id else None
        bucket["sources"].add(source_label or alert.source)

        bucket["alert_count"] += 1
        if alert.status == "firing":
            bucket["firing_count"] += 1
        if alert.severity:
            bucket["severities"].append(alert.severity)

        fired_at = alert.fired_at
        if fired_at and (bucket["last_fired_at"] is None or fired_at > bucket["last_fired_at"]):
            bucket["last_fired_at"] = fired_at

        type_bucket = bucket["types"].get(alert_type)
        if type_bucket is None:
            type_bucket = {
                "type": alert_type,
                "type_label": type_label,
                "count": 0,
                "firing_count": 0,
                "severities": [],
            }
            bucket["types"][alert_type] = type_bucket
        type_bucket["count"] += 1
        if alert.status == "firing":
            type_bucket["firing_count"] += 1
        if alert.severity:
            type_bucket["severities"].append(alert.severity)

    results: List[Dict[str, Any]] = []
    for bucket in instances.values():
        types_sorted = sorted(
            bucket["types"].values(),
            key=lambda t: (-t["count"], t["type"]),
        )
        type_items = []
        for t in types_sorted:
            type_items.append(
                {
                    "type": t["type"],
                    "type_label": t["type_label"],
                    "count": t["count"],
                    "firing_count": t["firing_count"],
                    "max_severity": max_severity(t["severities"]),
                }
            )
        results.append(
            {
                "instance_key": bucket["instance_key"],
                "instance_name": bucket["instance_name"],
                "instance_id": bucket["instance_id"],
                "ip": bucket["ip"],
                "sources": sorted(s for s in bucket["sources"] if s),
                "alert_count": bucket["alert_count"],
                "firing_count": bucket["firing_count"],
                "max_severity": max_severity(bucket["severities"]),
                "last_fired_at": bucket["last_fired_at"],
                "types": type_items,
            }
        )
    return results


def sort_instances(
    items: List[Dict[str, Any]],
    sort_by: str = "alert_count",
    sort_order: str = "desc",
) -> List[Dict[str, Any]]:
    """按告警数 / 严重级别 / 最近触发排序。

    severity: rank 数值越小越严重（critical=0）。desc=最严重在前。
    """
    reverse = sort_order != "asc"

    def sort_key(item: Dict[str, Any]):
        if sort_by == "max_severity":
            rank = SEVERITY_ORDER.get(item.get("max_severity") or "", 99)
            count = item.get("alert_count", 0)
            # desc: critical(rank 0) 在前 → key=rank；asc: info 在前 → key=-rank
            return (rank if reverse else -rank, -count if reverse else count)
        if sort_by == "last_fired_at":
            ts = item.get("last_fired_at")
            if isinstance(ts, datetime):
                value = -ts.timestamp() if reverse else ts.timestamp()
                return (0, value)
            return (1, 0)
        count = item.get("alert_count", 0)
        return (-count if reverse else count, item.get("instance_key") or "")

    return sorted(items, key=sort_key)


def build_scan_filters(
    tenant_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    window_days: int = SCAN_WINDOW_DAYS,
) -> List[Any]:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    filters = [
        Alert.tenant_id == str(tenant_id),
        Alert.status != "aggregated",
        Alert.fired_at >= since,
    ]
    if status:
        filters.append(Alert.status == status)
    if severity:
        filters.append(Alert.severity == severity)
    if source:
        filters.append(Alert.source == source)
    return filters


async def fetch_alerts_for_scan(
    db: AsyncSession,
    tenant_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = MAX_SCAN,
) -> Tuple[List[Alert], Dict[int, str], bool]:
    """按 fired_at desc 拉取扫描窗口内告警。返回 (alerts, source_name_map, truncated)。"""
    filters = build_scan_filters(tenant_id, status, severity, source)
    query = (
        select(Alert, AlertSource.name.label("source_name"))
        .outerjoin(AlertSource, Alert.source_id == AlertSource.id)
        .where(and_(*filters))
        .order_by(Alert.fired_at.desc())
        .limit(limit + 1)
    )
    result = await db.execute(query)
    rows = result.all()
    truncated = len(rows) > limit
    rows = rows[:limit]

    source_names: Dict[int, str] = {}
    alerts: List[Alert] = []
    for row in rows:
        alert = row[0]
        source_name = row[1]
        if alert.source_id and source_name:
            source_names[alert.source_id] = source_name
        alerts.append(alert)
    return alerts, source_names, truncated


def paginate_instances(
    items: List[Dict[str, Any]],
    keyword: Optional[str],
    page: int,
    page_size: int,
) -> Tuple[List[Dict[str, Any]], int]:
    if keyword:
        kw = keyword.strip().lower()
        items = [
            item
            for item in items
            if kw in (item.get("instance_key") or "").lower()
            or kw in (item.get("instance_name") or "").lower()
            or kw in (item.get("ip") or "").lower()
        ]
    total = len(items)
    start = (page - 1) * page_size
    return items[start : start + page_size], total


def filter_instance_alerts(
    alerts: List[Alert],
    instance_key: str,
    alert_type: Optional[str] = None,
) -> List[Alert]:
    matched = []
    for alert in alerts:
        info = extract_instance(alert)
        if info["instance_key"] != instance_key:
            continue
        if alert_type:
            code, _ = classify_alert_type(alert)
            if code != alert_type:
                continue
        matched.append(alert)
    return matched


def build_alert_items(
    alerts: List[Alert],
    source_names: Optional[Dict[int, str]] = None,
) -> List[AlertResponse]:
    source_names = source_names or {}
    items = []
    for alert in alerts:
        source_name = source_names.get(alert.source_id) if alert.source_id else None
        items.append(build_alert_response(alert, source_name))
    return items


def paginate_alerts(
    alerts: List[Alert],
    page: int,
    page_size: int,
) -> Tuple[List[Alert], int]:
    total = len(alerts)
    start = (page - 1) * page_size
    return alerts[start : start + page_size], total
