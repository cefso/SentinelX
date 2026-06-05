"""
SentinelX - 指纹视图列表（含虚拟策略聚合指纹行）
"""
from typing import List

from sqlalchemy import and_, func, literal, select, union_all, Integer, String
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


async def list_alerts_fingerprint_aggregate(
    db: AsyncSession,
    tenant_id: str,
    base_filter: List,
    page: int,
    page_size: int,
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

    fp_subq = (
        select(
            Alert.fingerprint.label("row_key"),
            literal("fingerprint").label("row_type"),
            literal(None, type_=Integer).label("group_id"),
            literal(None, type_=String).label("group_label"),
            func.max(Alert.id).label("latest_id"),
            func.count(Alert.id).label("row_count"),
            func.max(Alert.fired_at).label("sort_at"),
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

    total_result = await db.execute(select(func.count()).select_from(combined))
    total = total_result.scalar() or 0

    page_result = await db.execute(
        select(combined)
        .order_by(combined.c.sort_at.desc())
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

    items: List[AlertAggregatedItem] = []
    for row in page_rows:
        alert_row = alert_map.get(row.latest_id)
        if not alert_row:
            continue
        alert_obj, source_name = alert_row
        row_type = row.row_type
        group_count = row.row_count
        is_strategy = row_type == "strategy_group"

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
            )
        )

    return AlertAggregatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
