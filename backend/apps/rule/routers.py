"""
SentinelX - 规则管理路由
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from apps.core.database import get_db
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.rule.models import AlertRule
from apps.alert.models import Alert, AlertSource
from apps.tenant.models import User, UserTenant
from apps.core.redis import RedisClient
from apps.rule.schemas import (
    RuleCreate, RuleUpdate, RuleResponse, RuleTestRequest, RuleTestResponse,
    FieldValuesResponse, FieldValueItem,
    PreviewDedupRequest, PreviewAggregateRequest,
    PreviewDedupResponse, PreviewAggregateResponse, AlertGroupItem,
)

router = APIRouter()

# 支持的字段路径
SUPPORTED_SIMPLE_FIELDS = {
    "namespace",
    "source",
    "metric_name",
    "instance_id",
    "instance_name",
    "status",
}


# ============ 规则管理 ============

@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(
    is_active: Optional[bool] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取规则列表"""
    query = select(AlertRule).where(AlertRule.tenant_id == str(tenant_id))
    if is_active is not None:
        query = query.where(AlertRule.is_active == is_active)
    query = query.order_by(AlertRule.priority.desc(), AlertRule.id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    request: RuleCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建规则"""
    rule = AlertRule(
        tenant_id=str(tenant_id),
        name=request.name,
        code=request.code,
        description=request.description,
        conditions=[c.model_dump() for c in request.conditions],
        condition_mode=request.condition_mode,
        actions=request.actions,
        priority=request.priority,
        is_active=request.is_active,
        suppress_config=request.suppress_config,
        aggregate_config=request.aggregate_config,
        deduplication_config=request.deduplication_config,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/rules/field-values", response_model=FieldValuesResponse)
async def get_field_values(
    field: str = Query(..., description="字段路径，如 namespace/labels.cluster"),
    search: str = Query("", description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    获取规则条件字段的可选值列表（用于前端下拉补全）

    支持的字段:
    - 简单字段: namespace, source, metric_name, instance_id, instance_name
    - JSON标签: labels.cluster, labels.env, labels.service, labels (返回所有key)
    """
    # status 枚举值（固定）
    if field == "status":
        return await _get_status_field_values(search, limit, offset)

    # assignee 从 users 表查询
    if field == "assignee":
        return await _get_assignee_field_values(db, tenant_id, search, limit, offset)

    # alert_key 从 alerts 表查询（带 Redis 缓存）
    if field == "alert_key":
        return await _get_alert_key_field_values(db, tenant_id, search, limit, offset)

    # 检查是否是 source 字段（从 alert_sources 表查询）
    if field == "source":
        return await _get_source_field_values(db, tenant_id, search, limit, offset)

    # 检查是否是简单字段（从 alerts 表的列直接查询）
    if field in SUPPORTED_SIMPLE_FIELDS:
        return await _get_simple_field_values(db, tenant_id, field, search, limit, offset)

    # 检查是否是 JSON 标签字段（支持 labels 和 labels.{任意key}）
    if field == "labels" or field.startswith("labels."):
        return await _get_label_field_values(db, tenant_id, field, search, limit, offset)

    # 不支持的字段
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported field: {field}. "
               f"Supported: {', '.join(sorted(SUPPORTED_SIMPLE_FIELDS | {'labels', 'labels.*'} | {'assignee', 'alert_key'}))}"
    )


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取规则详情"""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == str(tenant_id)
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    request: RuleUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新规则"""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == str(tenant_id)
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = request.model_dump(exclude_unset=True)
    if "conditions" in update_data:
        update_data["conditions"] = [c.model_dump() if hasattr(c, 'model_dump') else c for c in update_data["conditions"]]

    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """删除规则"""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == str(tenant_id)
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
    return {"message": "Rule deleted successfully"}


@router.post("/rules/test", response_model=RuleTestResponse)
async def test_rule(
    request: RuleTestRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """测试规则条件"""
    from apps.rule.engine import RuleEngine

    engine = RuleEngine()
    matched, reason, evaluated = engine.evaluate_conditions(
        request.conditions,
        request.condition_mode,
        request.test_data
    )

    return RuleTestResponse(
        matched=matched,
        reason=reason,
        evaluated_conditions=evaluated,
    )


@router.post("/rules/preview-dedup", response_model=PreviewDedupResponse)
async def preview_dedup(
    request: PreviewDedupRequest,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    预览去重效果 - 根据去重配置返回符合条件的告警列表
    """
    from apps.alert.schemas import AlertResponse

    dedup_cfg = request.deduplication_config
    filters = [Alert.tenant_id == str(tenant_id)]

    # 基础过滤
    if request.status:
        filters.append(Alert.status == request.status)
    if request.severity:
        filters.append(Alert.severity == request.severity)
    if request.source:
        filters.append(Alert.source == request.source)

    # 时间窗口过滤
    window_seconds = getattr(dedup_cfg, "window_seconds", 300)
    from datetime import timedelta, datetime as dt
    window_start = dt.utcnow() - timedelta(seconds=window_seconds)
    filters.append(Alert.fired_at >= window_start)

    # 按去重类型构建查询
    if dedup_cfg.dedup_type == "fingerprint":
        # 指纹模式: 按 fingerprint_fields 构建组合 key 进行分组
        fp_fields = getattr(dedup_cfg, "fingerprint_fields", ["alert_key"])
        dimensions = getattr(dedup_cfg, "dimensions", None)

        # 构建 group_by 列表
        group_by_cols = []
        for field in fp_fields:
            col = _get_alert_column(field)
            if col is not None:
                group_by_cols.append(col)

        # 添加维度字段
        if dimensions:
            if getattr(dimensions, "by_severity", False):
                group_by_cols.append(Alert.severity)
            if getattr(dimensions, "by_source", False):
                group_by_cols.append(Alert.source)

        if not group_by_cols:
            group_by_cols = [Alert.fingerprint]

        # 构建分组查询: 每组的最新告警
        subq = (
            select(
                *group_by_cols,
                func.max(Alert.id).label("max_id"),
                func.count(Alert.id).label("count"),
            )
            .where(and_(*filters))
            .group_by(*group_by_cols)
            .subquery()
        )

        # 总分组数
        total_result = await db.execute(select(func.count()).select_from(subq))
        total = total_result.scalar() or 0

        # 分页子查询
        paginated_subq = (
            select(subq.c.max_id, subq.c.count)
            .order_by(subq.c.max_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )

        result = await db.execute(
            select(Alert, paginated_subq.c.count)
            .join(paginated_subq, Alert.id == paginated_subq.c.max_id)
            .order_by(Alert.fired_at.desc())
        )
        rows = result.all()

        items = [AlertResponse.model_validate(row.Alert) for row in rows]
        return PreviewDedupResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    else:
        # 条件模式: 用条件过滤
        conditions = getattr(dedup_cfg, "conditions", [])
        condition_mode = getattr(dedup_cfg, "condition_mode", "and")

        if conditions:
            from apps.rule.engine import RuleEngine
            engine = RuleEngine()

            # 先查询所有满足基础过滤的告警
            base_query = select(Alert).where(and_(*filters))
            result = await db.execute(base_query.order_by(Alert.fired_at.desc()))
            all_alerts = result.scalars().all()

            # 用规则引擎评估条件
            filtered = []
            for alert in all_alerts:
                alert_data = _alert_to_dict(alert)
                matched, _, _ = engine.evaluate_conditions(conditions, condition_mode, alert_data)
                if matched:
                    filtered.append(alert)

            total = len(filtered)
            paginated = filtered[(page - 1) * page_size:page * page_size]
            items = [AlertResponse.model_validate(a) for a in paginated]
        else:
            total = 0
            items = []

        return PreviewDedupResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )


@router.post("/rules/preview-aggregate", response_model=PreviewAggregateResponse)
async def preview_aggregate(
    request: PreviewAggregateRequest,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    预览聚合效果 - 根据聚合配置返回告警分组列表
    """
    from apps.alert.schemas import AlertResponse

    agg_cfg = request.aggregate_config
    filters = [Alert.tenant_id == str(tenant_id)]

    # 基础过滤
    if request.status:
        filters.append(Alert.status == request.status)
    if request.severity:
        filters.append(Alert.severity == request.severity)
    if request.source:
        filters.append(Alert.source == request.source)

    # 时间窗口过滤
    window_seconds = getattr(agg_cfg, "window_seconds", 300)
    from datetime import timedelta, datetime as dt
    window_start = dt.utcnow() - timedelta(seconds=window_seconds)
    filters.append(Alert.fired_at >= window_start)

    # 构建 group_by 列
    group_by_fields = getattr(agg_cfg, "group_by", [])
    group_by_cols = []
    for field in group_by_fields:
        col = _get_alert_column(field)
        if col is not None:
            group_by_cols.append(col)

    if not group_by_cols:
        group_by_cols = [Alert.fingerprint]

    # 分组查询: 每组最新告警和数量
    subq = (
        select(
            *group_by_cols,
            func.max(Alert.id).label("max_id"),
            func.count(Alert.id).label("count"),
        )
        .where(and_(*filters))
        .group_by(*group_by_cols)
        .subquery()
    )

    # 总分组数
    total_result = await db.execute(select(func.count()).select_from(subq))
    total = total_result.scalar() or 0

    # 分页子查询
    paginated_subq = (
        select(subq.c.max_id, subq.c.count)
        .order_by(subq.c.max_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .subquery()
    )

    result = await db.execute(
        select(Alert, paginated_subq.c.count)
        .join(paginated_subq, Alert.id == paginated_subq.c.max_id)
        .order_by(Alert.fired_at.desc())
    )
    rows = result.all()

    items = []
    for row in rows:
        group_key_parts = []
        for col in group_by_cols:
            val = getattr(row.Alert, col.key if hasattr(col, 'key') else col.name, None)
            if val is not None:
                group_key_parts.append(str(val))
        group_key = "/".join(group_key_parts) if group_key_parts else row.Alert.fingerprint

        items.append(AlertGroupItem(
            group_key=group_key,
            group_count=row.count,
            latest=AlertResponse.model_validate(row.Alert),
        ))

    return PreviewAggregateResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def _get_alert_column(field: str):
    """将字段路径映射为 Alert 模型列"""
    SIMPLE_FIELDS = {
        "alert_key": Alert.alert_key,
        "fingerprint": Alert.fingerprint,
        "source": Alert.source,
        "severity": Alert.severity,
        "status": Alert.status,
        "namespace": Alert.namespace,
        "instance_id": Alert.instance_id,
        "instance_name": Alert.instance_name,
        "metric_name": Alert.metric_name,
        "title": Alert.title,
    }

    if field in SIMPLE_FIELDS:
        return SIMPLE_FIELDS[field]

    # labels.xxx -> 需要用 JSONB 表达式
    if field.startswith("labels."):
        label_key = field.split(".", 1)[1]
        return func.jsonb_extract_path_text(Alert.labels, label_key).label(field)

    return None


def _alert_to_dict(alert: Alert) -> dict:
    """将 Alert 模型转换为字典，用于规则引擎评估"""
    return {
        "id": alert.id,
        "tenant_id": alert.tenant_id,
        "alert_key": alert.alert_key,
        "fingerprint": alert.fingerprint,
        "source": alert.source,
        "title": alert.title,
        "content": alert.content,
        "severity": alert.severity,
        "status": alert.status,
        "labels": alert.labels or {},
        "annotations": alert.annotations or {},
        "metric_name": alert.metric_name,
        "metric_value": alert.metric_value,
        "namespace": alert.namespace,
        "instance_id": alert.instance_id,
        "instance_name": alert.instance_name,
        "trace_id": alert.trace_id,
        "fire_count": alert.fire_count,
        "repeat_count": alert.repeat_count,
        "escalation_count": alert.escalation_count,
        "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
    }


# ============ 字段值查询 ============

STATUS_FIELD_VALUES = [
    FieldValueItem(value="firing", count=0),
    FieldValueItem(value="resolved", count=0),
    FieldValueItem(value="suppressed", count=0),
    FieldValueItem(value="acknowledged", count=0),
]

STATUS_CHINESE_LABELS = {
    "firing": "触发中",
    "resolved": "已恢复",
    "suppressed": "已抑制",
    "acknowledged": "已确认",
}


async def _get_status_field_values(
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """返回 status 固定枚举值"""
    # 过滤搜索关键词
    filtered = [item for item in STATUS_FIELD_VALUES
               if not search or search.lower() in item.value or search in STATUS_CHINESE_LABELS.get(item.value, "")]
    total = len(filtered)
    values = filtered[offset:offset + limit]
    return FieldValuesResponse(field="status", values=values, total=total, limit=limit, offset=offset)


async def _get_assignee_field_values(
    db: AsyncSession,
    tenant_id: int,
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """从 users + user_tenants 表查询用户列表"""
    tenant_str = str(tenant_id)

    query = (
        select(
            User.id.label("user_id"),
            User.username.label("user_name"),
        )
        .join(UserTenant, UserTenant.user_id == User.id)
        .where(UserTenant.tenant_id == tenant_str)
        .where(User.is_active == True)
    )

    if search:
        query = query.where(User.username.ilike(f"%{search}%"))

    query = query.order_by(User.username)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取分页结果
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    values = [
        FieldValueItem(value=str(row.user_id), count=0)
        for row in rows
    ]
    return FieldValuesResponse(field="assignee", values=values, total=total, limit=limit, offset=offset)


async def _get_alert_key_field_values(
    db: AsyncSession,
    tenant_id: int,
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """从 alerts 表获取 alert_key 去重列表（带 Redis 缓存）"""
    tenant_str = str(tenant_id)
    redis = RedisClient.get()

    cache_key = f"field_values:{tenant_str}:alert_key"
    cached = await redis.get(cache_key)

    if cached:
        # 从缓存中获取
        all_keys = json.loads(cached)
    else:
        # 查询数据库
        query = (
            select(
                Alert.alert_key,
                func.count(Alert.id).label("count"),
            )
            .where(Alert.tenant_id == tenant_str)
            .group_by(Alert.alert_key)
            .order_by(func.count(Alert.id).desc())
        )
        result = await db.execute(query)
        rows = result.all()
        all_keys = [{"value": row.alert_key, "count": row.count} for row in rows]

        # 写入 Redis 缓存（5分钟 TTL）
        await redis.set(cache_key, json.dumps(all_keys), ex=300)

    # 应用搜索过滤
    if search:
        filtered = [k for k in all_keys if search.lower() in k["value"].lower()]
    else:
        filtered = all_keys

    total = len(filtered)
    page = filtered[offset:offset + limit]
    values = [FieldValueItem(value=item["value"], count=item["count"]) for item in page]
    return FieldValuesResponse(field="alert_key", values=values, total=total, limit=limit, offset=offset)


async def _get_source_field_values(
    db: AsyncSession,
    tenant_id: int,
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """从 alert_sources 表获取 source 字段值"""
    tenant_str = str(tenant_id)

    # 构建查询
    query = (
        select(
            AlertSource.code.label("value"),
            func.count(AlertSource.id).label("count"),
        )
        .where(AlertSource.tenant_id == tenant_str)
    )

    if search:
        query = query.where(AlertSource.code.ilike(f"%{search}%"))

    query = (
        query
        .group_by(AlertSource.code)
        .order_by(func.count(AlertSource.id).desc())
    )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取分页结果
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    values = [FieldValueItem(value=row.value, count=row.count) for row in rows]
    return FieldValuesResponse(field="source", values=values, total=total, limit=limit, offset=offset)


async def _get_simple_field_values(
    db: AsyncSession,
    tenant_id: int,
    field: str,
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """从 alerts 表获取简单字段值（namespace, metric_name, instance_id, instance_name）"""
    tenant_str = str(tenant_id)
    field_column = getattr(Alert, field)

    # 构建查询
    query = (
        select(
            field_column.label("value"),
            func.count(Alert.id).label("count"),
        )
        .where(Alert.tenant_id == tenant_str)
        .where(field_column.isnot(None))
    )

    if search:
        query = query.where(field_column.ilike(f"%{search}%"))

    query = (
        query
        .group_by(field_column)
        .order_by(func.count(Alert.id).desc())
    )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取分页结果
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # 过滤掉空字符串值
    values = [
        FieldValueItem(value=row.value, count=row.count)
        for row in rows
        if row.value is not None and row.value != ""
    ]
    return FieldValuesResponse(field=field, values=values, total=total, limit=limit, offset=offset)


async def _get_label_field_values(
    db: AsyncSession,
    tenant_id: int,
    field: str,
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """
    从 alerts.labels JSONB 字段获取标签值

    支持:
    - labels: 返回所有出现过的标签 key
    - labels.cluster / labels.env / labels.service: 返回指定 key 的所有值
    """
    tenant_str = str(tenant_id)

    if field == "labels":
        # 返回所有 labels 中出现过的 key
        return await _get_label_keys(db, tenant_str, search, limit, offset)

    # labels.cluster / labels.env / labels.service
    # 提取 path 部分的 key: labels.cluster -> "cluster"
    parts = field.split(".")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail=f"Invalid label path: {field}")

    label_key = parts[1]

    # 使用 PostgreSQL jsonb_extract_path_text 获取标签值
    # 同时用 jsonb_typeof 确保该 key 存在
    label_value = func.jsonb_extract_path_text(Alert.labels, label_key).label("value")

    query = (
        select(
            label_value,
            func.count(Alert.id).label("count"),
        )
        .where(Alert.tenant_id == tenant_str)
        .where(func.jsonb_typeof(Alert.labels[label_key]).isnot(None))
    )

    if search:
        query = query.where(label_value.ilike(f"%{search}%"))

    query = (
        query
        .group_by(label_value)
        .order_by(func.count(Alert.id).desc())
    )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取分页结果
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # 过滤掉空字符串
    values = [
        FieldValueItem(value=row.value, count=row.count)
        for row in rows
        if row.value is not None and row.value != ""
    ]
    return FieldValuesResponse(field=field, values=values, total=total, limit=limit, offset=offset)


async def _get_label_keys(
    db: AsyncSession,
    tenant_id: str,
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """返回 alerts.labels 中所有出现过的标签 key"""
    # 使用 jsonb_object_keys 提取所有 key
    key_expr = func.jsonb_object_keys(Alert.labels).label("key")

    query = (
        select(
            key_expr,
            func.count(Alert.id).label("count"),
        )
        .where(Alert.tenant_id == tenant_id)
    )

    if search:
        query = query.where(key_expr.ilike(f"%{search}%"))

    query = (
        query
        .group_by(key_expr)
        .order_by(func.count(Alert.id).desc())
    )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 获取分页结果
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # 将 key 作为 value 返回，count 为出现该 key 的告警数
    values = [
        FieldValueItem(value=row.key, count=row.count)
        for row in rows
    ]
    return FieldValuesResponse(field="labels", values=values, total=total, limit=limit, offset=offset)

