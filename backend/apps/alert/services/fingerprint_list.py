"""
SentinelX - 指纹视图列表（含虚拟策略聚合指纹行 + 抖动检测）
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlalchemy import and_, func, literal, select, union_all, Integer, String, case
from sqlalchemy.ext.asyncio import AsyncSession

from apps.alert.models import (
    Alert,
    AlertAggregateGroup,
    AlertAggregateMember,
    AlertSource,
)
from apps.alert.schemas import AlertAggregatedItem, AlertAggregatedResponse
from apps.alert.services.alert_utils import build_alert_response
from apps.rule.models import AlertRule

STRATEGY_GROUP_FP_PREFIX = "strategy-group:"
# 条件B 最近 N 条 / 时间窗上界，避免无界扫描
FLAPPING_RECENT_LIMIT = 10
FLAPPING_LOOKBACK_HOURS = 24 * 7
STALE_HOURS = 24


def _strategy_group_fingerprint(group_id: int) -> str:
    return f"{STRATEGY_GROUP_FP_PREFIX}{group_id}"


async def _load_recent_alerts_per_fingerprint(
    db: AsyncSession,
    tenant_id: int,
    fingerprints: Sequence[str],
    limit_per_fp: int = FLAPPING_RECENT_LIMIT,
    lookback_hours: int = FLAPPING_LOOKBACK_HOURS,
) -> dict[str, list]:
    """每个 fingerprint 只取最近 limit 条（窗口函数），禁止全量拉取。"""
    if not fingerprints:
        return {}

    lookback_start = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    rn = func.row_number().over(
        partition_by=Alert.fingerprint,
        order_by=Alert.fired_at.desc(),
    ).label("rn")

    ranked = (
        select(
            Alert.fingerprint,
            Alert.status,
            Alert.fired_at,
            Alert.resolved_at,
            rn,
        )
        .where(
            and_(
                Alert.tenant_id == tenant_id,
                Alert.fingerprint.in_(list(fingerprints)),
                Alert.fired_at >= lookback_start,
            )
        )
        .subquery()
    )

    result = await db.execute(
        select(
            ranked.c.fingerprint,
            ranked.c.status,
            ranked.c.fired_at,
            ranked.c.resolved_at,
        )
        .where(ranked.c.rn <= limit_per_fp)
        .order_by(ranked.c.fingerprint, ranked.c.fired_at.desc())
    )

    fp_alerts: dict[str, list] = defaultdict(list)
    for row in result.all():
        fp_alerts[row.fingerprint].append(row)
    return fp_alerts


def _is_flapping_from_recent(recent_alerts: list) -> bool:
    """条件B：最近告警中 firing→resolved 交替 >= 2 且平均持续 < 10 分钟。"""
    if len(recent_alerts) < 3:
        return False

    alternations = 0
    durations = []
    for i in range(len(recent_alerts) - 1):
        curr_status = recent_alerts[i].status
        prev_status = recent_alerts[i + 1].status
        if (prev_status == "firing" and curr_status == "resolved") or (
            prev_status == "resolved" and curr_status == "firing"
        ):
            alternations += 1
        if recent_alerts[i].resolved_at and recent_alerts[i].fired_at:
            dur = (recent_alerts[i].resolved_at - recent_alerts[i].fired_at).total_seconds()
            durations.append(dur)

    if alternations >= 2 and durations:
        avg_duration = sum(durations) / len(durations)
        return avg_duration < 600
    return False


async def _condition_a_flapping_fingerprints(
    db: AsyncSession,
    tenant_id: int,
    extra_filter: Optional[List] = None,
) -> set:
    """条件A：1小时内同 fingerprint 告警数 >= 3。"""
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    conditions = [
        Alert.tenant_id == tenant_id,
        Alert.fired_at >= one_hour_ago,
    ]
    if extra_filter:
        conditions.extend(extra_filter)

    freq_result = await db.execute(
        select(Alert.fingerprint)
        .where(and_(*conditions))
        .group_by(Alert.fingerprint)
        .having(func.count() >= 3)
    )
    return {row[0] for row in freq_result.all()}


async def _candidate_fingerprints_for_condition_b(
    db: AsyncSession,
    tenant_id: int,
    extra_filter: Optional[List] = None,
    exclude: Optional[set] = None,
) -> List[str]:
    """找出可能满足条件B 的 fingerprint（有界：时间窗内 >=3 条）。"""
    lookback_start = datetime.now(timezone.utc) - timedelta(hours=FLAPPING_LOOKBACK_HOURS)
    conditions = [
        Alert.tenant_id == tenant_id,
        Alert.fired_at >= lookback_start,
    ]
    if extra_filter:
        conditions.extend(extra_filter)

    result = await db.execute(
        select(Alert.fingerprint)
        .where(and_(*conditions))
        .group_by(Alert.fingerprint)
        .having(func.count() >= 3)
    )
    fps = [row[0] for row in result.all()]
    if exclude:
        fps = [fp for fp in fps if fp not in exclude]
    return fps


async def _detect_flapping_fingerprints(
    db: AsyncSession,
    tenant_id: int,
    fingerprints: List[str],
) -> set:
    """检测抖动告警的 fingerprint 集合。

    抖动条件（满足任一）：
    条件A: 1小时内同 fingerprint 告警数 >= 3
    条件B: 最近10条告警中 firing→resolved 交替 >= 2 次，且平均持续时间 < 10 分钟
    """
    if not fingerprints:
        return set()

    flapping_fps = await _condition_a_flapping_fingerprints(
        db, tenant_id, [Alert.fingerprint.in_(fingerprints)]
    )

    remaining = [fp for fp in fingerprints if fp not in flapping_fps]
    if remaining:
        fp_alerts = await _load_recent_alerts_per_fingerprint(db, tenant_id, remaining)
        for fp in remaining:
            if _is_flapping_from_recent(fp_alerts.get(fp, [])):
                flapping_fps.add(fp)

    return flapping_fps


async def _detect_flapping_fingerprints_for_filter(
    db: AsyncSession,
    tenant_id: int,
    base_filter: List,
) -> set:
    """在分页前，对匹配 base_filter 的全量候选 fingerprint 做有界抖动检测。"""
    cond_a = await _condition_a_flapping_fingerprints(db, tenant_id, base_filter)
    candidates = await _candidate_fingerprints_for_condition_b(
        db, tenant_id, base_filter, exclude=cond_a
    )
    flapping_fps = set(cond_a)
    if candidates:
        fp_alerts = await _load_recent_alerts_per_fingerprint(db, tenant_id, candidates)
        for fp in candidates:
            if _is_flapping_from_recent(fp_alerts.get(fp, [])):
                flapping_fps.add(fp)
    return flapping_fps


async def list_alerts_fingerprint_aggregate(
    db: AsyncSession,
    tenant_id: int,
    base_filter: List,
    page: int,
    page_size: int,
    flapping_only: bool = False,
    stale_only: bool = False,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> AlertAggregatedResponse:
    """指纹视图：真实 fingerprint 分组 + 虚拟策略聚合指纹行合并分页。"""

    strategy_member_ids = (
        select(AlertAggregateMember.alert_id)
        .join(
            AlertAggregateGroup,
            AlertAggregateGroup.id == AlertAggregateMember.group_id,
        )
        .where(
            AlertAggregateGroup.tenant_id == tenant_id,
            AlertAggregateGroup.alert_count > 1,
        )
    )

    fp_filter = list(base_filter) + [Alert.id.not_in(strategy_member_ids)]

    flapping_set: set = set()
    # flapping_only：分页前算出有界 flapping 集合并下推 WHERE
    if flapping_only:
        flapping_set = await _detect_flapping_fingerprints_for_filter(
            db, tenant_id, list(base_filter)
        )
        if not flapping_set:
            return AlertAggregatedResponse(
                items=[],
                total=0,
                alert_total=0,
                page=page,
                page_size=page_size,
            )
        fp_filter.append(Alert.fingerprint.in_(flapping_set))

    severity_order = case(
        (Alert.severity == "critical", 1),
        (Alert.severity == "high", 2),
        (Alert.severity == "medium", 3),
        (Alert.severity == "low", 4),
        (Alert.severity == "info", 5),
        else_=6,
    )

    fp_subq = (
        select(
            Alert.fingerprint.label("row_key"),
            literal("fingerprint").label("row_type"),
            literal(None, type_=Integer).label("group_id"),
            literal(None, type_=String).label("group_label"),
            func.max(Alert.id).label("latest_id"),
            func.count(Alert.id).label("row_count"),
            func.max(Alert.fired_at).label("sort_at"),
            func.min(severity_order).label("severity_rank"),
        )
        .where(and_(*fp_filter))
        .group_by(Alert.fingerprint)
    )

    strategy_base_filter = list(base_filter)
    if flapping_only:
        strategy_base_filter.append(Alert.fingerprint.in_(flapping_set))

    strategy_subq = (
        select(
            func.concat(literal(STRATEGY_GROUP_FP_PREFIX), AlertAggregateGroup.id).label("row_key"),
            literal("strategy_group").label("row_type"),
            AlertAggregateGroup.id.label("group_id"),
            func.coalesce(AlertRule.name, AlertAggregateGroup.group_key).label("group_label"),
            func.min(AlertAggregateMember.alert_id).label("latest_id"),
            AlertAggregateGroup.alert_count.label("row_count"),
            func.max(Alert.fired_at).label("sort_at"),
            func.min(severity_order).label("severity_rank"),
        )
        .select_from(AlertAggregateGroup)
        .join(
            AlertAggregateMember,
            AlertAggregateMember.group_id == AlertAggregateGroup.id,
        )
        .join(Alert, Alert.id == AlertAggregateMember.alert_id)
        .outerjoin(AlertRule, AlertRule.id == AlertAggregateGroup.rule_id)
        .where(
            AlertAggregateGroup.tenant_id == tenant_id,
            AlertAggregateGroup.alert_count > 1,
            and_(*strategy_base_filter),
        )
        .group_by(
            AlertAggregateGroup.id,
            AlertAggregateGroup.alert_count,
            AlertAggregateGroup.group_key,
            AlertRule.name,
        )
    )

    combined = union_all(fp_subq, strategy_subq).subquery()

    # stale_only：最新告警为 firing 且 sort_at 超过 24h，在分页前过滤
    stale_threshold = datetime.now(timezone.utc) - timedelta(hours=STALE_HOURS)
    if stale_only:
        stmt = (
            select(combined)
            .join(Alert, Alert.id == combined.c.latest_id)
            .where(
                combined.c.row_type == "fingerprint",
                combined.c.sort_at < stale_threshold,
                Alert.status == "firing",
            )
        )
    else:
        stmt = select(combined)

    # 动态排序
    if sort_by == "severity":
        order_col = combined.c.severity_rank
    elif sort_by == "count":
        order_col = combined.c.row_count
    else:
        order_col = combined.c.sort_at

    if sort_order == "asc":
        order_clause = order_col.asc()
    else:
        order_clause = order_col.desc()

    total_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = total_result.scalar() or 0

    alert_total_result = await db.execute(
        select(func.sum(stmt.subquery().c.row_count))
    )
    alert_total = int(alert_total_result.scalar() or 0)

    page_result = await db.execute(
        stmt.order_by(order_clause).offset((page - 1) * page_size).limit(page_size)
    )
    page_rows = page_result.all()

    if not page_rows:
        return AlertAggregatedResponse(
            items=[],
            total=total,
            alert_total=alert_total,
            page=page,
            page_size=page_size,
        )

    latest_ids = [row.latest_id for row in page_rows]
    alerts_result = await db.execute(
        select(Alert, AlertSource.name.label("source_name"))
        .outerjoin(AlertSource, Alert.source_id == AlertSource.id)
        .where(Alert.id.in_(latest_ids))
    )
    alert_map = {row.Alert.id: (row.Alert, row.source_name) for row in alerts_result.all()}

    # 当页抖动标记（未 flapping_only 时）
    if flapping_only:
        flapping_fps = flapping_set
    else:
        fp_list = [row.row_key for row in page_rows if row.row_type == "fingerprint"]
        flapping_fps = await _detect_flapping_fingerprints(db, tenant_id, fp_list)

    now = datetime.now(timezone.utc)

    items: List[AlertAggregatedItem] = []
    for row in page_rows:
        alert_row = alert_map.get(row.latest_id)
        if not alert_row:
            continue
        alert_obj, source_name = alert_row
        row_type = row.row_type
        group_count = row.row_count
        is_strategy = row_type == "strategy_group"

        is_stale = (
            not is_strategy
            and alert_obj.status == "firing"
            and row.sort_at is not None
            and row.sort_at.replace(tzinfo=timezone.utc) < stale_threshold
        )

        items.append(
            AlertAggregatedItem(
                fingerprint=row.row_key,
                count=group_count,
                latest=build_alert_response(
                    alert_obj,
                    source_name,
                    aggregate_group_count=group_count if is_strategy else None,
                ),
                row_type=row_type,
                aggregate_group_id=row.group_id if is_strategy else None,
                group_label=row.group_label if is_strategy else None,
                flapping=row.row_key in flapping_fps,
                stale=is_stale,
            )
        )

    return AlertAggregatedResponse(
        items=items,
        total=total,
        alert_total=alert_total,
        page=page,
        page_size=page_size,
    )
