"""
SentinelX - 指纹视图列表（含虚拟策略聚合指纹行 + 抖动检测）
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

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


def _strategy_group_fingerprint(group_id: int) -> str:
    return f"{STRATEGY_GROUP_FP_PREFIX}{group_id}"


async def _detect_flapping_fingerprints(
    db: AsyncSession,
    tenant_id: str,
    fingerprints: List[str],
) -> set:
    """检测抖动告警的 fingerprint 集合。

    抖动条件（满足任一）：
    条件A: 1小时内同 fingerprint 告警数 >= 3
    条件B: 最近10条告警中 firing→resolved 交替 >= 2 次，且平均持续时间 < 10 分钟
    """
    if not fingerprints:
        return set()

    flapping_fps = set()

    # 条件A: 1小时内频率 >= 3
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    freq_result = await db.execute(
        select(Alert.fingerprint)
        .where(
            and_(
                Alert.tenant_id == tenant_id,
                Alert.fingerprint.in_(fingerprints),
                Alert.fired_at >= one_hour_ago,
            )
        )
        .group_by(Alert.fingerprint)
        .having(func.count() >= 3)
    )
    flapping_fps.update(row[0] for row in freq_result.all())

    # 条件B: 交替模式 + 短持续时间（仅对尚未标记的 fingerprint 检测）
    remaining = [fp for fp in fingerprints if fp not in flapping_fps]
    if remaining:
        for fp in remaining:
            recent_result = await db.execute(
                select(Alert.status, Alert.fired_at, Alert.resolved_at)
                .where(
                    and_(
                        Alert.tenant_id == tenant_id,
                        Alert.fingerprint == fp,
                    )
                )
                .order_by(Alert.fired_at.desc())
                .limit(10)
            )
            recent_alerts = recent_result.all()
            if len(recent_alerts) < 3:
                continue

            # 计算 firing→resolved 交替次数
            alternations = 0
            durations = []
            for i in range(len(recent_alerts) - 1):
                curr_status = recent_alerts[i].status
                prev_status = recent_alerts[i + 1].status
                if (prev_status == "firing" and curr_status == "resolved") or \
                   (prev_status == "resolved" and curr_status == "firing"):
                    alternations += 1
                # 计算持续时间
                if recent_alerts[i].resolved_at and recent_alerts[i].fired_at:
                    dur = (recent_alerts[i].resolved_at - recent_alerts[i].fired_at).total_seconds()
                    durations.append(dur)

            if alternations >= 2 and durations:
                avg_duration = sum(durations) / len(durations)
                if avg_duration < 600:  # 10分钟
                    flapping_fps.add(fp)

    return flapping_fps


async def list_alerts_fingerprint_aggregate(
    db: AsyncSession,
    tenant_id: str,
    base_filter: List,
    page: int,
    page_size: int,
    flapping_only: bool = False,
    stale_only: bool = False,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> AlertAggregatedResponse:
    """指纹视图：真实 fingerprint 分组 + 虚拟策略聚合指纹行合并分页。"""
    tenant_str = str(tenant_id)

    strategy_member_ids = (
        select(AlertAggregateMember.alert_id)
        .join(
            AlertAggregateGroup,
            AlertAggregateGroup.id == AlertAggregateMember.group_id,
        )
        .where(
            AlertAggregateGroup.tenant_id == tenant_str,
            AlertAggregateGroup.alert_count > 1,
        )
    )

    fp_filter = list(base_filter) + [Alert.id.not_in(strategy_member_ids)]

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
            AlertAggregateGroup.tenant_id == tenant_str,
            AlertAggregateGroup.alert_count > 1,
            and_(*base_filter),
        )
        .group_by(
            AlertAggregateGroup.id,
            AlertAggregateGroup.alert_count,
            AlertAggregateGroup.group_key,
            AlertRule.name,
        )
    )

    combined = union_all(fp_subq, strategy_subq).subquery()

    # 动态排序
    if sort_by == "severity":
        order_col = combined.c.severity_rank
    elif sort_by == "count":
        order_col = combined.c.row_count
    else:
        # 默认按持续时长（sort_at）排序
        order_col = combined.c.sort_at

    if sort_order == "asc":
        order_clause = order_col.asc()
    else:
        order_clause = order_col.desc()

    total_result = await db.execute(select(func.count()).select_from(combined))
    total = total_result.scalar() or 0

    # 计算实际告警总数（所有指纹的告警数之和）
    alert_total_result = await db.execute(
        select(func.sum(combined.c.row_count)).select_from(combined)
    )
    alert_total = int(alert_total_result.scalar() or 0)

    page_result = await db.execute(
        select(combined)
        .order_by(order_clause)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    page_rows = page_result.all()

    if not page_rows:
        return AlertAggregatedResponse(
            items=[],
            total=total,
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

    # 检测抖动告警
    fp_list = [row.row_key for row in page_rows if row.row_type == "fingerprint"]
    flapping_fps = await _detect_flapping_fingerprints(db, tenant_str, fp_list)

    # 检测长时间未更新告警（最新消息超24h且未恢复）
    now = datetime.now(timezone.utc)
    stale_threshold = now - timedelta(hours=24)

    items: List[AlertAggregatedItem] = []
    for row in page_rows:
        alert_row = alert_map.get(row.latest_id)
        if not alert_row:
            continue
        alert_obj, source_name = alert_row
        row_type = row.row_type
        group_count = row.row_count
        is_strategy = row_type == "strategy_group"

        # stale: 最新告警是 firing 且 sort_at 超过 24h
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

    # 后置过滤：flapping_only / stale_only
    if flapping_only:
        items = [item for item in items if item.flapping]
    if stale_only:
        items = [item for item in items if item.stale]

    return AlertAggregatedResponse(
        items=items,
        total=total,
        alert_total=alert_total,
        page=page,
        page_size=page_size,
    )
