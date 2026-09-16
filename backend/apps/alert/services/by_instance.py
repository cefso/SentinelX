"""
实例维度告警聚合：实例识别、类型分类、分组统计。
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.alert.models import Alert, AlertSource
from apps.alert.schemas import AlertResponse
from apps.alert.services.alert_utils import build_alert_response, extract_instance_from_title

UNKNOWN_INSTANCE_KEY = "__unknown__"

SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

TYPE_LABELS = {
    "cpu": "CPU",
    "memory": "内存",
    "disk": "磁盘",
    "process": "进程",
    "network": "网络",
    "other": "其他",
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


def extract_instance(alert: Alert) -> Dict[str, Optional[str]]:
    """多字段兜底识别实例。instance_key 用于聚合，instance_name 用于展示。

    优先级：instance_name → instance_id → labels.host → labels.instance
            → 标题「xx 的 [..]」首段（lcmdb）→ labels.ip → 未识别
    lcmdb 入库时会写入 instance_name；历史数据仍走标题/IP 兜底。
    """
    labels = alert.labels or {}
    ip = _clean(labels.get("ip"))
    instance_name = _clean(alert.instance_name)
    instance_id = _clean(alert.instance_id)
    host = _clean(labels.get("host"))
    instance_label = _clean(labels.get("instance"))

    if instance_name:
        return {
            "instance_key": instance_name,
            "instance_name": instance_name,
            "instance_id": instance_id,
            "ip": ip,
        }

    title_name = extract_instance_from_title(alert.title or "")

    key = (
        instance_id
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
        shown_name = title_name or instance_id or host or instance_label or ip

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


def severity_rank(severity: Optional[str]) -> int:
    """critical=0 … unknown/None=5；与 SQL CASE 保持一致。"""
    if not severity:
        return 5
    return SEVERITY_ORDER.get(severity, 5)


def severity_from_rank(rank: Optional[int]) -> Optional[str]:
    if rank is None or rank < 0 or rank >= len(SEVERITY_ORDER):
        return None
    inverse = {v: k for k, v in SEVERITY_ORDER.items()}
    return inverse.get(rank)


def apply_instance_denorm(alert: Alert) -> None:
    """就地写入 alert.instance_key / alert.alert_type。

    与查询期 extract_instance / classify_alert_type 同源；无法识别写 __unknown__/other。
    instance_key 截断至 256，避免超长 labels.host/instance 插入失败。
    """
    info = extract_instance(alert)
    key = info["instance_key"] or UNKNOWN_INSTANCE_KEY
    alert.instance_key = key[:256]
    alert_type, _ = classify_alert_type(alert)
    alert.alert_type = alert_type or "other"


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
    tenant_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    window_days: int = SCAN_WINDOW_DAYS,
) -> List[Any]:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    filters = [
        Alert.tenant_id == tenant_id,
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
    tenant_id: int,
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


def _severity_rank_case():
    return case(
        (Alert.severity == "critical", 0),
        (Alert.severity == "high", 1),
        (Alert.severity == "medium", 2),
        (Alert.severity == "low", 3),
        (Alert.severity == "info", 4),
        else_=5,
    )


def _instance_key_col():
    """展示/聚合用表达式；等值过滤请用 _instance_key_match 以走 B-tree 索引。"""
    return func.coalesce(Alert.instance_key, UNKNOWN_INSTANCE_KEY)


def _instance_key_match(instance_key: str):
    """索引友好的 instance_key 谓词：__unknown__ 对应 NULL 列，其余等值。"""
    if instance_key == UNKNOWN_INSTANCE_KEY:
        return Alert.instance_key.is_(None)
    return Alert.instance_key == instance_key


def _instance_key_any(keys: List[str]):
    """当页 key 的 OR 谓词，避免 COALESCE(...) IN (...) 放弃索引。"""
    conditions = []
    for key in keys:
        conditions.append(_instance_key_match(key))
    return or_(*conditions) if conditions else (Alert.id.is_(None))


def _ip_col():
    return Alert.labels.op("->>")("ip")


def _base_filters(
    tenant_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    window_days: Optional[int] = SCAN_WINDOW_DAYS,
) -> List[Any]:
    filters: List[Any] = [
        Alert.tenant_id == tenant_id,
        Alert.status != "aggregated",
    ]
    if window_days:
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        filters.append(Alert.fired_at >= since)
    if status:
        filters.append(Alert.status == status)
    if severity:
        filters.append(Alert.severity == severity)
    if source:
        filters.append(Alert.source == source)
    return filters


async def list_instances_sql(
    db: AsyncSession,
    tenant_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "alert_count",
    sort_order: str = "desc",
    window_days: int = SCAN_WINDOW_DAYS,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """SQL 聚合实例卡片。返回 (page_items, total_instances, scanned_alerts)。"""
    filters = _base_filters(tenant_id, status, severity, source, window_days)
    instance_key_col = _instance_key_col()
    rank_col = _severity_rank_case()
    source_label = func.coalesce(AlertSource.name, Alert.source)
    instance_name_col = func.max(Alert.instance_name).filter(
        Alert.instance_name.isnot(None) & (Alert.instance_name != "")
    )
    ip_col = func.max(_ip_col()).filter(_ip_col().isnot(None) & (_ip_col() != ""))

    base = (
        select(
            instance_key_col.label("instance_key"),
            func.count(Alert.id).label("alert_count"),
            func.count(Alert.id).filter(Alert.status == "firing").label("firing_count"),
            func.max(Alert.fired_at).label("last_fired_at"),
            instance_name_col.label("instance_name"),
            func.max(Alert.instance_id)
            .filter(Alert.instance_id.isnot(None) & (Alert.instance_id != ""))
            .label("instance_id"),
            ip_col.label("ip"),
            func.min(rank_col).label("severity_rank"),
            func.array_agg(func.distinct(source_label)).label("sources"),
        )
        .select_from(Alert)
        .outerjoin(AlertSource, Alert.source_id == AlertSource.id)
        .where(and_(*filters))
        .group_by(instance_key_col)
    )

    # 组级 keyword：与旧「先分组再过滤卡片」语义一致
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        base = base.having(
            or_(
                instance_key_col.ilike(pattern),
                instance_name_col.ilike(pattern),
                ip_col.ilike(pattern),
            )
        )

    if sort_by == "max_severity":
        order = func.min(rank_col).asc() if sort_order != "asc" else func.min(rank_col).desc()
        order_by = [order, func.count(Alert.id).desc(), instance_key_col.asc()]
    elif sort_by == "last_fired_at":
        order = (
            func.max(Alert.fired_at).desc()
            if sort_order != "asc"
            else func.max(Alert.fired_at).asc()
        )
        order_by = [order, instance_key_col.asc()]
    else:
        order = (
            func.count(Alert.id).desc() if sort_order != "asc" else func.count(Alert.id).asc()
        )
        order_by = [order, instance_key_col.asc()]

    count_q = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_q)).scalar() or 0)

    scanned_q = select(func.count(Alert.id)).where(and_(*filters))
    scanned = int((await db.execute(scanned_q)).scalar() or 0)

    offset = (page - 1) * page_size
    page_q = base.order_by(*order_by).limit(page_size).offset(offset)
    rows = (await db.execute(page_q)).all()

    page_keys = [row.instance_key for row in rows]
    types_by_key: Dict[str, List[Dict[str, Any]]] = {}
    if page_keys:
        type_rank = _severity_rank_case()
        alert_type_col = func.coalesce(Alert.alert_type, "other")
        type_q = (
            select(
                instance_key_col.label("instance_key"),
                alert_type_col.label("alert_type"),
                func.count(Alert.id).label("count"),
                func.count(Alert.id).filter(Alert.status == "firing").label("firing_count"),
                func.min(type_rank).label("severity_rank"),
            )
            .select_from(Alert)
            .where(and_(*filters, _instance_key_any(page_keys)))
            .group_by(instance_key_col, alert_type_col)
        )
        for trow in (await db.execute(type_q)).all():
            code = trow.alert_type or "other"
            types_by_key.setdefault(trow.instance_key, []).append(
                {
                    "type": code,
                    "type_label": TYPE_LABELS.get(code, "其他"),
                    "count": trow.count,
                    "firing_count": trow.firing_count or 0,
                    "max_severity": severity_from_rank(trow.severity_rank),
                }
            )

    items: List[Dict[str, Any]] = []
    for row in rows:
        types_sorted = sorted(
            types_by_key.get(row.instance_key, []),
            key=lambda t: (-t["count"], t["type"]),
        )
        items.append(
            {
                "instance_key": row.instance_key,
                "instance_name": row.instance_name,
                "instance_id": row.instance_id,
                "ip": row.ip,
                "sources": sorted(s for s in (row.sources or []) if s),
                "alert_count": row.alert_count,
                "firing_count": row.firing_count or 0,
                "max_severity": severity_from_rank(row.severity_rank),
                "last_fired_at": row.last_fired_at,
                "types": types_sorted,
            }
        )
    return items, total, scanned


async def list_instance_alerts_sql(
    db: AsyncSession,
    tenant_id: int,
    instance_key: str,
    alert_type: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    window_days: int = SCAN_WINDOW_DAYS,
) -> Tuple[List[AlertResponse], int]:
    """某实例（可选某类型）告警明细：SQL 过滤 + 分页。"""
    filters = _base_filters(tenant_id, status, severity, source, window_days)
    filters.append(_instance_key_match(instance_key))
    if alert_type:
        filters.append(func.coalesce(Alert.alert_type, "other") == alert_type)

    total = int(
        (await db.execute(select(func.count(Alert.id)).where(and_(*filters)))).scalar() or 0
    )

    offset = (page - 1) * page_size
    q = (
        select(Alert, AlertSource.name.label("source_name"))
        .outerjoin(AlertSource, Alert.source_id == AlertSource.id)
        .where(and_(*filters))
        .order_by(Alert.fired_at.desc(), Alert.id.desc())
        .limit(page_size)
        .offset(offset)
    )
    rows = (await db.execute(q)).all()
    items = [build_alert_response(row[0], row[1]) for row in rows]
    return items, total
