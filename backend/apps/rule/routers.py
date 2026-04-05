"""
SentinelX - 规则管理路由
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.core.database import get_db
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.rule.models import AlertRule, NotificationChannel, NotificationTemplate
from apps.alert.models import Alert, AlertSource
from apps.tenant.models import User, UserTenant
from apps.core.redis import RedisClient
from apps.rule.schemas import (
    RuleCreate, RuleUpdate, RuleResponse, RuleTestRequest, RuleTestResponse,
    ChannelCreate, ChannelUpdate, ChannelResponse,
    TemplateCreate, TemplateUpdate, TemplateResponse,
    FieldValuesResponse, FieldValueItem,
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
SUPPORTED_LABEL_PATHS = {
    "labels",
    "labels.cluster",
    "labels.env",
    "labels.service",
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


# ============ 通知渠道管理 ============

@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    is_active: Optional[bool] = None,
    channel_type: Optional[str] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知渠道列表"""
    query = select(NotificationChannel).where(NotificationChannel.tenant_id == str(tenant_id))
    if is_active is not None:
        query = query.where(NotificationChannel.is_active == is_active)
    if channel_type:
        query = query.where(NotificationChannel.channel_type == channel_type)
    result = await db.execute(query.order_by(NotificationChannel.id))
    return result.scalars().all()


@router.post("/channels", response_model=ChannelResponse)
async def create_channel(
    request: ChannelCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建通知渠道"""
    channel = NotificationChannel(
        tenant_id=str(tenant_id),
        name=request.name,
        code=request.code,
        channel_type=request.channel_type,
        config=request.config,
        is_active=request.is_active,
        is_default=request.is_default,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.put("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    request: ChannelUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新通知渠道"""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == str(tenant_id)
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)
    return channel


# ============ 通知模板管理 ============

@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    channel_type: Optional[str] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知模板列表"""
    query = select(NotificationTemplate).where(NotificationTemplate.tenant_id == str(tenant_id))
    if channel_type:
        query = query.where(NotificationTemplate.channel_type == channel_type)
    result = await db.execute(query.order_by(NotificationTemplate.id))
    return result.scalars().all()


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建通知模板"""
    template = NotificationTemplate(
        tenant_id=str(tenant_id),
        name=request.name,
        code=request.code,
        channel_type=request.channel_type,
        content=request.content,
        variables=request.variables,
        is_active=request.is_active,
        is_default=request.is_default,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    request: TemplateUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新通知模板"""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == str(tenant_id)
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template
