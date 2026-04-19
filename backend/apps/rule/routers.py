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
from apps.alert.services.alert_utils import alert_to_dict
from apps.tenant.models import User, UserTenant
from apps.core.redis import RedisClient
import re as _re
import unicodedata
from apps.rule.schemas import (
    RuleCreate, RuleUpdate, RuleResponse, RuleTestRequest, RuleTestResponse,
    FieldValuesResponse, FieldValueItem,
    PreviewDedupRequest, PreviewAggregateRequest,
    PreviewDedupResponse, PreviewAggregateResponse, AlertGroupItem,
    StrategyRuleCreate, StrategyRuleUpdate, StrategyRuleResponse,
    RuleAction,
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


async def _validate_template_ids(
    db: AsyncSession,
    tenant_id: int,
    actions: list,
) -> None:
    """验证 actions 中的 template_id 属于同一 tenant 且 channel_type 匹配"""
    if not actions:
        return

    from apps.rule.models import NotificationTemplate, NotificationChannel

    for action in actions:
        template_id = None
        channel_id = None

        if isinstance(action, str):
            # 旧格式: "1" -> 纯渠道ID，无需验证
            continue
        elif isinstance(action, dict):
            # 新格式: {"channel_id": 1, "template_id": 5}
            channel_id = action.get("channel_id")
            template_id = action.get("template_id")
        elif hasattr(action, "channel_id"):
            channel_id = action.channel_id
            template_id = getattr(action, "template_id", None)

        if template_id is None:
            continue

        # 查询模板
        result = await db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.id == template_id,
                NotificationTemplate.tenant_id == str(tenant_id),
                NotificationTemplate.is_active == True,
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(
                status_code=400,
                detail=f"Template {template_id} not found or not accessible"
            )

        # 查询渠道
        if channel_id:
            channel_result = await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.id == channel_id,
                    NotificationChannel.tenant_id == str(tenant_id),
                )
            )
            channel = channel_result.scalar_one_or_none()
            if not channel:
                raise HTTPException(
                    status_code=400,
                    detail=f"Channel {channel_id} not found"
                )
            # 验证 channel_type 匹配
            if template.channel_type != channel.channel_type:
                raise HTTPException(
                    status_code=400,
                    detail=f"Template {template_id} (type: {template.channel_type}) does not match channel {channel_id} (type: {channel.channel_type})"
                )


# ============ 规则管理 ============

@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(
    is_active: Optional[bool] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取规则列表"""
    query = select(AlertRule).where(
        AlertRule.tenant_id == str(tenant_id),
        AlertRule.name != STRATEGY_RULE_NAME,
        ~AlertRule.code.like('_dedup_%'),
        ~AlertRule.code.like('_suppress_%'),
        ~AlertRule.code.like('_aggregate_%'),
    )
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
    # 验证 actions 中的 template_id
    await _validate_template_ids(db, tenant_id, request.actions)

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
    - 枚举字段: status, severity
    - 简单字段: namespace, source, metric_name, instance_id, instance_name
    - JSON标签: labels.cluster, labels.env, labels.service, labels (返回所有key)
    """
    # status 枚举值（固定）
    if field == "status":
        return await _get_status_field_values(search, limit, offset)

    # severity 枚举值（固定）
    if field == "severity":
        return await _get_severity_field_values(search, limit, offset)

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
    # 验证 actions 中的 template_id
    if request.actions is not None:
        await _validate_template_ids(db, tenant_id, request.actions)

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


# ============ 策略规则 CRUD ============

STRATEGY_RULE_NAME = "_strategy_config"

# 策略类型 -> code 前缀映射
_STRATEGY_PREFIXES = {
    "dedup": "_dedup_",
    "suppress": "_suppress_",
    "aggregate": "_aggregate_",
}

# 策略类型 -> 配置字段映射
_STRATEGY_CONFIG_FIELDS = {
    "dedup": "deduplication_config",
    "suppress": "suppress_config",
    "aggregate": "aggregate_config",
}


def _slugify(name: str) -> str:
    """将名称转换为 slug"""
    # 简单的 slug 生成：小写 + 去特殊字符
    slug = _re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if slug:
        return slug[:40]
    # 兜底：中文/纯特殊字符名称时使用时间戳
    from datetime import datetime
    return datetime.now().strftime('%Y%m%d%H%M%S')


def _build_strategy_crud(prefix: str, config_field: str):
    """为策略类型构建 CRUD 端点工厂"""

    async def list_strategy_rules(
        is_active: Optional[bool] = None,
        tenant_id: int = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ):
        """获取策略规则列表"""
        query = select(AlertRule).where(
            AlertRule.tenant_id == str(tenant_id),
            AlertRule.code.like(f'{prefix}%'),
        )
        if is_active is not None:
            query = query.where(AlertRule.is_active == is_active)
        query = query.order_by(AlertRule.priority.desc(), AlertRule.id)
        result = await db.execute(query)
        return result.scalars().all()

    async def create_strategy_rule(
        request: StrategyRuleCreate,
        tenant_id: int = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ):
        """创建策略规则"""
        slug = _slugify(request.name)
        code = f"{prefix}{slug}"
        rule = AlertRule(
            tenant_id=str(tenant_id),
            name=request.name,
            code=code,
            description=request.description,
            conditions=[c.model_dump() for c in request.conditions],
            condition_mode=request.condition_mode,
            actions=[],
            priority=request.priority,
            is_active=request.is_active,
        )
        setattr(rule, config_field, request.config)
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule

    async def get_strategy_rule(
        rule_id: int,
        tenant_id: int = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ):
        """获取策略规则详情"""
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.id == rule_id,
                AlertRule.tenant_id == str(tenant_id),
                AlertRule.code.like(f'{prefix}%'),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Strategy rule not found")
        return rule

    async def update_strategy_rule(
        rule_id: int,
        request: StrategyRuleUpdate,
        tenant_id: int = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ):
        """更新策略规则"""
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.id == rule_id,
                AlertRule.tenant_id == str(tenant_id),
                AlertRule.code.like(f'{prefix}%'),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Strategy rule not found")

        update_data = request.model_dump(exclude_unset=True)
        if "conditions" in update_data:
            update_data["conditions"] = [
                c.model_dump() if hasattr(c, 'model_dump') else c
                for c in update_data["conditions"]
            ]
        if "config" in update_data:
            setattr(rule, config_field, update_data.pop("config"))

        for field, value in update_data.items():
            setattr(rule, field, value)

        await db.commit()
        await db.refresh(rule)
        return rule

    async def delete_strategy_rule(
        rule_id: int,
        tenant_id: int = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ):
        """删除策略规则"""
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.id == rule_id,
                AlertRule.tenant_id == str(tenant_id),
                AlertRule.code.like(f'{prefix}%'),
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="Strategy rule not found")

        await db.delete(rule)
        await db.commit()
        return {"message": "Strategy rule deleted successfully"}

    return list_strategy_rules, create_strategy_rule, get_strategy_rule, update_strategy_rule, delete_strategy_rule


# 创建三组 CRUD 端点
_list_dedup, _create_dedup, _get_dedup, _update_dedup, _delete_dedup = _build_strategy_crud("_dedup_", "deduplication_config")
_list_suppress, _create_suppress, _get_suppress, _update_suppress, _delete_suppress = _build_strategy_crud("_suppress_", "suppress_config")
_list_aggregate, _create_aggregate, _get_aggregate, _update_aggregate, _delete_aggregate = _build_strategy_crud("_aggregate_", "aggregate_config")

# 注册去重规则端点
router.add_api_route("/rules/dedup-rules", _list_dedup, methods=["GET"], response_model=list[StrategyRuleResponse], name="list_dedup_rules")
router.add_api_route("/rules/dedup-rules", _create_dedup, methods=["POST"], response_model=StrategyRuleResponse, name="create_dedup_rule")
router.add_api_route("/rules/dedup-rules/{rule_id}", _get_dedup, methods=["GET"], response_model=StrategyRuleResponse, name="get_dedup_rule")
router.add_api_route("/rules/dedup-rules/{rule_id}", _update_dedup, methods=["PUT"], response_model=StrategyRuleResponse, name="update_dedup_rule")
router.add_api_route("/rules/dedup-rules/{rule_id}", _delete_dedup, methods=["DELETE"], name="delete_dedup_rule")

# 注册抑制规则端点
router.add_api_route("/rules/suppress-rules", _list_suppress, methods=["GET"], response_model=list[StrategyRuleResponse], name="list_suppress_rules")
router.add_api_route("/rules/suppress-rules", _create_suppress, methods=["POST"], response_model=StrategyRuleResponse, name="create_suppress_rule")
router.add_api_route("/rules/suppress-rules/{rule_id}", _get_suppress, methods=["GET"], response_model=StrategyRuleResponse, name="get_suppress_rule")
router.add_api_route("/rules/suppress-rules/{rule_id}", _update_suppress, methods=["PUT"], response_model=StrategyRuleResponse, name="update_suppress_rule")
router.add_api_route("/rules/suppress-rules/{rule_id}", _delete_suppress, methods=["DELETE"], name="delete_suppress_rule")

# 注册聚合规则端点
router.add_api_route("/rules/aggregate-rules", _list_aggregate, methods=["GET"], response_model=list[StrategyRuleResponse], name="list_aggregate_rules")
router.add_api_route("/rules/aggregate-rules", _create_aggregate, methods=["POST"], response_model=StrategyRuleResponse, name="create_aggregate_rule")
router.add_api_route("/rules/aggregate-rules/{rule_id}", _get_aggregate, methods=["GET"], response_model=StrategyRuleResponse, name="get_aggregate_rule")
router.add_api_route("/rules/aggregate-rules/{rule_id}", _update_aggregate, methods=["PUT"], response_model=StrategyRuleResponse, name="update_aggregate_rule")
router.add_api_route("/rules/aggregate-rules/{rule_id}", _delete_aggregate, methods=["DELETE"], name="delete_aggregate_rule")


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


def _build_preview_filters(
    tenant_id: int,
    status: Optional[str],
    severity: Optional[str],
    source: Optional[str],
    window_seconds: int = 300,
) -> list:
    """构建预览查询的通用过滤器列表"""
    from datetime import timedelta, datetime as dt, timezone

    filters = [Alert.tenant_id == str(tenant_id)]
    if status:
        filters.append(Alert.status == status)
    if severity:
        filters.append(Alert.severity == severity)
    if source:
        filters.append(Alert.source == source)

    window_start = dt.now(timezone.utc) - timedelta(seconds=window_seconds)
    filters.append(Alert.fired_at >= window_start)
    return filters


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
    window_seconds = getattr(dedup_cfg, "window_seconds", 300)
    filters = _build_preview_filters(
        tenant_id, request.status, request.severity, request.source, window_seconds
    )

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

        rows, total = await _build_grouped_alerts_query(db, filters, group_by_cols, page, page_size)
        items = [AlertResponse.model_validate(row.Alert) for row in rows]
        return PreviewDedupResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    else:
        # 条件模式: 用条件过滤（分批从数据库读取，避免内存溢出）
        conditions = getattr(dedup_cfg, "conditions", [])
        condition_mode = getattr(dedup_cfg, "condition_mode", "and")

        if not conditions:
            return PreviewDedupResponse(items=[], total=0, page=page, page_size=page_size)

        from apps.rule.engine import RuleEngine
        engine = RuleEngine()

        # 分批读取 + 规则引擎评估，收集够 page_size 条后停止
        BATCH_SIZE = 500
        collected = []
        offset = 0

        while len(collected) < (page - 1) * page_size + page_size:
            batch_query = (
                select(Alert)
                .where(and_(*filters))
                .order_by(Alert.fired_at.desc())
                .offset(offset)
                .limit(BATCH_SIZE)
            )
            result = await db.execute(batch_query)
            batch = result.scalars().all()

            if not batch:
                break

            for alert in batch:
                alert_data = alert_to_dict(alert)
                matched, _, _ = engine.evaluate_conditions(conditions, condition_mode, alert_data)
                if matched:
                    collected.append(alert)

            offset += BATCH_SIZE

        total = len(collected)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = collected[start_idx:end_idx]
        items = [AlertResponse.model_validate(a) for a in paginated]

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
    window_seconds = getattr(agg_cfg, "window_seconds", 300)
    filters = _build_preview_filters(
        tenant_id, request.status, request.severity, request.source, window_seconds
    )

    # 构建 group_by 列
    group_by_fields = getattr(agg_cfg, "group_by", [])
    group_by_cols = []
    for field in group_by_fields:
        col = _get_alert_column(field)
        if col is not None:
            group_by_cols.append(col)

    if not group_by_cols:
        group_by_cols = [Alert.fingerprint]

    rows, total = await _build_grouped_alerts_query(db, filters, group_by_cols, page, page_size)

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


async def _build_grouped_alerts_query(
    db: AsyncSession,
    filters: list,
    group_by_cols: list,
    page: int,
    page_size: int,
) -> tuple[list, int]:
    """
    构建分组告警查询（预览去重/聚合共用）

    返回: (rows, total) — rows 为 (Alert, count) 元组列表, total 为总分组数
    """
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
    return rows, total


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


SEVERITY_FIELD_VALUES = [
    FieldValueItem(value="critical", count=0),
    FieldValueItem(value="high", count=0),
    FieldValueItem(value="medium", count=0),
    FieldValueItem(value="low", count=0),
    FieldValueItem(value="info", count=0),
]

SEVERITY_CHINESE_LABELS = {
    "critical": "严重",
    "high": "高",
    "medium": "中",
    "low": "低",
    "info": "信息",
}


async def _get_severity_field_values(
    search: str,
    limit: int,
    offset: int,
) -> FieldValuesResponse:
    """返回 severity 固定枚举值"""
    filtered = [item for item in SEVERITY_FIELD_VALUES
               if not search or search.lower() in item.value or search in SEVERITY_CHINESE_LABELS.get(item.value, "")]
    total = len(filtered)
    values = filtered[offset:offset + limit]
    return FieldValuesResponse(field="severity", values=values, total=total, limit=limit, offset=offset)


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
    redis = await RedisClient.get_instance()

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

