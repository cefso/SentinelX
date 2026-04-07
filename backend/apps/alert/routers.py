"""
SentinelX - 告警管理路由
"""
import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, Integer, case, distinct, cast, Date

from apps.core.database import get_db
from apps.core.redis import get_redis
from apps.core.security import verify_password
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.alert.models import Alert, AlertSource, AlertHistory, AlertTrace, CloudProductMetric, AlertAggregateGroup, AlertAggregateMember
from apps.tenant.models import Tenant
from apps.alert.schemas import (
    AlertCreate, AlertUpdate, AlertResponse, AlertListResponse, AlertFilter, AlertStats,
    AlertSourceCreate, AlertSourceUpdate, AlertSourceResponse,
    AlertHistoryResponse, DiagnosisResponse, TraceStep,
    AlertAggregateMemberItem, AlertAggregateMembersResponse,
)
from apps.alert.services.dispatcher import AlertDispatcher

router = APIRouter()


def generate_fingerprint(alert: AlertCreate, tenant_id: str, source_id: int = None) -> str:
    """生成告警指纹"""
    fp_data = {
        "tenant_id": tenant_id,
        "source": alert.source,
        "source_id": str(source_id) if source_id else None,
        "alert_key": alert.alert_key,
        "labels": json.dumps(alert.labels, sort_keys=True, default=str),
    }
    fp_json = json.dumps(fp_data, sort_keys=True, default=str)
    return hashlib.sha256(fp_json.encode()).hexdigest()[:16]


def generate_trace_id() -> str:
    """生成12位Trace ID"""
    return str(uuid.uuid4())[:12]


async def _create_alerts_from_parsed(
    parsed_alert: AlertCreate | List[AlertCreate],
    tenant_id: str,
    db: AsyncSession,
    redis,
    background_tasks: BackgroundTasks,
    source_id: int = None,
) -> dict:
    """
    根据解析后的告警数据创建 Alert 记录并启动分发
    支持单条和批量创建
    """
    dispatcher = AlertDispatcher(db, redis)

    # 更新 AlertSource 统计
    if source_id:
        source = await db.get(AlertSource, source_id)
        if source and str(source.tenant_id) == tenant_id:
            source.alert_count = (source.alert_count or 0) + 1
            source.last_alert_at = datetime.utcnow()

    if isinstance(parsed_alert, list):
        results = []
        for alert_data in parsed_alert:
            trace_id = generate_trace_id()
            fingerprint = alert_data.fingerprint or generate_fingerprint(alert_data, tenant_id, source_id)

            alert = Alert(
                tenant_id=tenant_id,
                alert_key=alert_data.alert_key,
                fingerprint=fingerprint,
                source=alert_data.source,
                source_id=source_id,
                title=alert_data.title,
                content=alert_data.content,
                severity=alert_data.severity,
                status="firing",
                labels=alert_data.labels,
                annotations=alert_data.annotations,
                metric_name=alert_data.metric_name,
                metric_value=alert_data.metric_value,
                raw_data=alert_data.raw_data,
                namespace=alert_data.namespace,
                instance_id=alert_data.instance_id,
                instance_name=alert_data.instance_name,
                trace_id=trace_id,
                fired_at=datetime.utcnow(),
            )
            db.add(alert)
            await db.flush()

            background_tasks.add_task(dispatcher.dispatch, alert, trace_id)
            results.append({"id": None, "db_alert": alert})

        await db.commit()
        return {
            "received": len(results),
            "alerts": [{"id": r["db_alert"].id, "trace_id": r["db_alert"].trace_id} for r in results]
        }
    else:
        trace_id = generate_trace_id()
        fingerprint = parsed_alert.fingerprint or generate_fingerprint(parsed_alert, tenant_id, source_id)

        alert = Alert(
            tenant_id=tenant_id,
            alert_key=parsed_alert.alert_key,
            fingerprint=fingerprint,
            source=parsed_alert.source,
            source_id=source_id,
            title=parsed_alert.title,
            content=parsed_alert.content,
            severity=parsed_alert.severity,
            status="firing",
            labels=parsed_alert.labels,
            annotations=parsed_alert.annotations,
            metric_name=parsed_alert.metric_name,
            metric_value=parsed_alert.metric_value,
            raw_data=parsed_alert.raw_data,
            namespace=parsed_alert.namespace,
            instance_id=parsed_alert.instance_id,
            instance_name=parsed_alert.instance_name,
            trace_id=trace_id,
            fired_at=datetime.utcnow(),
        )
        db.add(alert)
        await db.flush()

        background_tasks.add_task(dispatcher.dispatch, alert, trace_id)

        await db.commit()
        await db.refresh(alert)
        return {"id": alert.id, "trace_id": alert.trace_id}


# ============ 告警源管理 ============

@router.get("/sources/stats")
async def get_sources_stats(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取各告警源的统计"""
    result = await db.execute(
        select(
            Alert.source_id,
            func.count(Alert.id).label("total"),
            func.sum(case((Alert.status == "firing", 1), else_=0)).label("firing"),
        )
        .where(
            and_(
                Alert.tenant_id == str(tenant_id),
                Alert.source_id.isnot(None),
            )
        )
        .group_by(Alert.source_id)
    )
    rows = result.all()

    return {
        "stats": [
            {
                "source_id": row.source_id,
                "total": row.total,
                "firing": row.firing or 0,
            }
            for row in rows
        ]
    }


@router.get("/sources", response_model=list[AlertSourceResponse])
async def list_sources(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取告警源列表"""
    result = await db.execute(
        select(AlertSource).where(
            AlertSource.tenant_id == tenant_id
        ).order_by(AlertSource.id)
    )
    return result.scalars().all()


@router.post("/sources", response_model=AlertSourceResponse)
async def create_source(
    request: AlertSourceCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建告警源"""
    source = AlertSource(
        tenant_id=tenant_id,
        name=request.name,
        code=request.code,
        source_type=request.source_type,
        config=request.config,
        description=request.description,
        client_id=request.client_id,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """删除告警源，保留关联告警"""
    source = await db.get(AlertSource, source_id)
    if not source or source.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="AlertSource not found")

    # 将告警的 source_id 设为 NULL
    await db.execute(
        Alert.__table__.update()
        .where(Alert.source_id == source_id)
        .values(source_id=None)
    )

    await db.delete(source)
    await db.commit()
    return {"message": "AlertSource deleted"}


@router.patch("/sources/{source_id}/toggle", response_model=AlertSourceResponse)
async def toggle_source(
    source_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """切换告警源启用/禁用状态"""
    source = await db.get(AlertSource, source_id)
    if not source or source.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="AlertSource not found")

    source.is_active = "inactive" if source.is_active == "active" else "active"
    await db.commit()
    await db.refresh(source)
    return source


# ============ 告警接入 ============

@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    request: AlertCreate,
    background_tasks: BackgroundTasks,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """接收告警"""
    trace_id = request.trace_id or generate_trace_id()
    fingerprint = request.fingerprint or generate_fingerprint(request, tenant_id, request.source_id)

    # 创建告警记录
    alert = Alert(
        tenant_id=tenant_id,
        alert_key=request.alert_key,
        fingerprint=fingerprint,
        source=request.source,
        source_id=request.source_id,
        title=request.title,
        content=request.content,
        severity=request.severity,
        status="firing",
        labels=request.labels,
        annotations=request.annotations,
        metric_name=request.metric_name,
        metric_value=request.metric_value,
        raw_data=request.raw_data,
        namespace=request.namespace,
        instance_id=request.instance_id,
        instance_name=request.instance_name,
        trace_id=trace_id,
        fired_at=datetime.utcnow(),
    )
    db.add(alert)
    await db.flush()

    # 启动后台分发处理
    dispatcher = AlertDispatcher(db, redis)
    background_tasks.add_task(dispatcher.dispatch, alert, trace_id)

    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/alerts/webhook/{source_type}")
async def receive_webhook_alert(
    source_type: str,
    raw_data: dict,
    background_tasks: BackgroundTasks,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    Webhook方式接收告警
    自动识别数据格式并转换为标准告警
    支持: prometheus, alertmanager, zabbix, aliyun, tencent, custom
    """
    from apps.alert.adapters import AdapterFactory

    # 获取适配器
    adapter = AdapterFactory.get_adapter(source_type)

    # 解析告警
    parsed_alert = await adapter.parse(raw_data, tenant_id)

    if not parsed_alert:
        raise HTTPException(status_code=400, detail=f"Unsupported alert format for source: {source_type}")

    return await _create_alerts_from_parsed(parsed_alert, tenant_id, db, redis, background_tasks)


@router.post("/webhooks/{tenant_slug}/{source_type}/{identifier}")
async def receive_webhook_by_source(
    tenant_slug: str,
    source_type: str,
    identifier: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    Webhook方式接收告警 (多租户版本，支持告警源)

    - tenant_slug: 租户 slug (如 sentinelx)
    - source_type: 告警源类型 (prometheus/grafana/zabbix/aliyun/aliyun_cms/aliyun_cms2/tencent/huawei/custom)
    - identifier: 告警源 client_id (或 id)
    - X-API-Key: 租户的 webhook API Key (可选)
    支持 Content-Type: application/json 和 application/x-www-form-urlencoded
    """
    from apps.alert.adapters import AdapterFactory
    from urllib.parse import unquote_plus

    # 1. 通过 tenant_slug 获取租户
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_slug}")

    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")

    tenant_id = str(tenant.id)

    # 2. 按 identifier 查找 AlertSource（支持 id 或 client_id）
    if identifier.isdigit():
        alert_source = await db.get(AlertSource, int(identifier))
    else:
        result = await db.execute(
            select(AlertSource).where(AlertSource.client_id == identifier)
        )
        alert_source = result.scalar_one_or_none()

    if not alert_source or str(alert_source.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail=f"AlertSource not found: {identifier}")

    # 3. 验证 API Key (可选)
    if x_api_key and tenant.webhook_api_key:
        if not verify_password(x_api_key, tenant.webhook_api_key):
            raise HTTPException(status_code=401, detail="Invalid webhook API key")

    # 4. 根据 Content-Type 解析请求数据
    content_type = request.headers.get("content-type", "").lower()

    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        raw_data = {}
        for key, value in form_data.items():
            if isinstance(value, bytes):
                value = unquote_plus(value.decode('utf-8'))
            raw_data[key] = value
    else:
        raw_data = await request.json()

    # 5. 获取适配器
    adapter = AdapterFactory.get_adapter(source_type)

    # 6. 解析告警
    parsed_alert = await adapter.parse(raw_data, tenant_id)

    if not parsed_alert:
        raise HTTPException(status_code=400, detail=f"Unsupported alert format for source: {source_type}")

    # 7. 处理告警
    return await _create_alerts_from_parsed(
        parsed_alert, tenant_id, db, redis, background_tasks, source_id=alert_source.id
    )


@router.post("/webhooks/{tenant_slug}/aliyun_cms/form")
async def receive_aliyun_cms_webhook(
    tenant_slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    阿里云云监控1.0 Webhook (Form Data格式) [已废弃]
    接收 application/x-www-form-urlencoded 格式的告警
    推荐使用: POST /webhooks/{tenant_slug}/aliyun_cms
    """
    from apps.alert.adapters import AdapterFactory
    from urllib.parse import unquote_plus

    # 1. 通过 tenant_slug 获取租户
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {tenant_slug}")

    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")

    # 2. 验证 API Key (可选，如果有配置的话)
    tenant_id = str(tenant.id)
    if x_api_key and tenant.webhook_api_key:
        if not verify_password(x_api_key, tenant.webhook_api_key):
            raise HTTPException(status_code=401, detail="Invalid webhook API key")

    # 3. 解析 form data
    form_data = await request.form()
    raw_data = {}
    for key, value in form_data.items():
        if isinstance(value, bytes):
            value = unquote_plus(value.decode('utf-8'))
        raw_data[key] = value

    # 4. 获取适配器
    adapter = AdapterFactory.get_adapter("aliyun_cms")

    # 5. 解析告警
    parsed_alert = await adapter.parse(raw_data, tenant_id)

    if not parsed_alert:
        raise HTTPException(status_code=400, detail="Unsupported alert format for source: aliyun_cms")

    # 6. 处理告警
    return await _create_alerts_from_parsed(parsed_alert, tenant_id, db, redis, background_tasks)


@router.post("/alerts/batch")
async def create_alerts_batch(
    alerts: List[AlertCreate],
    background_tasks: BackgroundTasks,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """批量接收告警"""
    created_alerts = []
    dispatcher = AlertDispatcher(db, redis)

    for alert_data in alerts:
        trace_id = alert_data.trace_id or generate_trace_id()
        fingerprint = alert_data.fingerprint or generate_fingerprint(alert_data, tenant_id, alert_data.source_id)

        alert = Alert(
            tenant_id=tenant_id,
            alert_key=alert_data.alert_key,
            fingerprint=fingerprint,
            source=alert_data.source,
            title=alert_data.title,
            content=alert_data.content,
            severity=alert_data.severity,
            status="firing",
            labels=alert_data.labels,
            annotations=alert_data.annotations,
            metric_name=alert_data.metric_name,
            metric_value=alert_data.metric_value,
            raw_data=alert_data.raw_data,
            namespace=alert_data.namespace,
            instance_id=alert_data.instance_id,
            instance_name=alert_data.instance_name,
            trace_id=trace_id,
            fired_at=datetime.utcnow(),
        )
        db.add(alert)
        await db.flush()
        created_alerts.append(alert)

        # 异步分发
        background_tasks.add_task(dispatcher.dispatch, alert, trace_id)

    await db.commit()
    return {"created": len(created_alerts), "alerts": created_alerts}


# ============ 告警查询 ============

@router.get("/alerts")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    aggregate: bool = Query(False),
    fingerprint: Optional[str] = None,
    source_id: Optional[int] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取告警列表，支持聚合模式"""
    base_filter = [Alert.tenant_id == str(tenant_id)]

    if status:
        base_filter.append(Alert.status == status)
    if severity:
        base_filter.append(Alert.severity.in_(severity))
    if source:
        base_filter.append(Alert.source == source)
    if keyword:
        base_filter.append(or_(
            Alert.title.ilike(f"%{keyword}%"),
            Alert.content.ilike(f"%{keyword}%")
        ))
    if start_time:
        base_filter.append(Alert.fired_at >= start_time)
    if end_time:
        base_filter.append(Alert.fired_at <= end_time)
    if fingerprint:
        base_filter.append(Alert.fingerprint == fingerprint)
    if source_id:
        base_filter.append(Alert.source_id == source_id)

    # 聚合模式
    if aggregate:
        from apps.alert.schemas import AlertAggregatedResponse, AlertAggregatedItem

        # 子查询: 每 fingerprint 的最新告警 ID 和数量
        subq = (
            select(
                Alert.fingerprint,
                func.max(Alert.id).label("max_id"),
                func.count(Alert.id).label("count"),
            )
            .where(and_(*base_filter))
            .group_by(Alert.fingerprint)
            .subquery()
        )

        # 总分组数
        total_result = await db.execute(select(func.count()).select_from(subq))
        total = total_result.scalar() or 0

        # 分页子查询
        paginated_subq = (
            select(subq.c.fingerprint, subq.c.max_id, subq.c.count)
            .order_by(subq.c.max_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )

        # 关联获取完整告警
        # 注意: 需要在 JOIN 条件中再次应用 base_filter，确保返回的 Alert 符合过滤条件
        alert_filter = [Alert.id == paginated_subq.c.max_id]
        if severity:
            alert_filter.append(Alert.severity.in_(severity))

        result = await db.execute(
            select(Alert, paginated_subq.c.count)
            .join(paginated_subq, and_(*alert_filter))
            .order_by(Alert.fired_at.desc())
        )
        rows = result.all()

        items = [
            AlertAggregatedItem(
                fingerprint=row.Alert.fingerprint,
                count=row.count,
                latest=row.Alert,
            )
            for row in rows
        ]

        return AlertAggregatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    # 普通模式
    query = select(Alert).where(and_(*base_filter))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Alert.fired_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        items=alerts,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/alerts/stats", response_model=AlertStats)
async def get_alert_stats(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取告警统计"""
    tenant_filter = Alert.tenant_id == str(tenant_id)

    # 查询1: 总数 + 按状态分布 (1次DB调用)
    status_result = await db.execute(
        select(
            func.count(),
            func.sum(case((Alert.status == "firing", 1), else_=0)),
            func.sum(case((Alert.status == "resolved", 1), else_=0)),
            func.sum(case((Alert.status == "suppressed", 1), else_=0)),
        ).where(tenant_filter)
    )
    row = status_result.one()
    total = row[0] or 0
    firing = row[1] or 0
    resolved = row[2] or 0
    suppressed = row[3] or 0

    # 查询2: 按严重级别分布 (仅 firing 状态, 1次DB调用)
    severity_result = await db.execute(
        select(
            func.sum(case((and_(Alert.status == "firing", Alert.severity == "critical"), 1), else_=0)),
            func.sum(case((and_(Alert.status == "firing", Alert.severity == "high"), 1), else_=0)),
            func.sum(case((and_(Alert.status == "firing", Alert.severity == "medium"), 1), else_=0)),
            func.sum(case((and_(Alert.status == "firing", Alert.severity == "low"), 1), else_=0)),
            func.sum(case((and_(Alert.status == "firing", Alert.severity == "info"), 1), else_=0)),
            func.sum(case((and_(Alert.status == "firing", Alert.assignee_id == None), 1), else_=0)),
        ).where(tenant_filter)
    )
    sev_row = severity_result.one()
    critical = sev_row[0] or 0
    high = sev_row[1] or 0
    medium = sev_row[2] or 0
    low = sev_row[3] or 0
    info = sev_row[4] or 0
    unassigned = sev_row[5] or 0

    # 查询3: 去重数量 (不同 fingerprint)
    unique_result = await db.execute(
        select(func.count(distinct(Alert.fingerprint))).where(tenant_filter)
    )
    unique = unique_result.scalar() or 0

    # 查询4: 今日新增
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count()).where(
            and_(tenant_filter, Alert.fired_at >= today_start)
        )
    )
    today = today_result.scalar() or 0

    return AlertStats(
        total=total,
        firing=firing,
        resolved=resolved,
        suppressed=suppressed,
        critical=critical,
        high=high,
        medium=medium,
        low=low,
        info=info,
        unassigned=unassigned,
        unique=unique,
        today=today,
        firing_critical=critical,
        firing_high=high,
    )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取告警详情"""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == str(tenant_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/alerts/{alert_id}/aggregated-members", response_model=AlertAggregateMembersResponse)
async def get_aggregated_members(
    alert_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取聚合告警组成员"""
    # 查找告警是否存在
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == str(tenant_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 查找该告警所属的聚合组
    member_result = await db.execute(
        select(AlertAggregateMember).where(AlertAggregateMember.alert_id == alert_id)
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Alert is not part of any aggregate group")

    group_id = member.group_id

    # 获取聚合组信息
    group = await db.get(AlertAggregateGroup, group_id)
    if not group or group.tenant_id != str(tenant_id):
        raise HTTPException(status_code=404, detail="Aggregate group not found")

    # 统计总数
    count_result = await db.execute(
        select(func.count()).select_from(AlertAggregateMember).where(AlertAggregateMember.group_id == group_id)
    )
    total = count_result.scalar() or 0

    # 分页查询组成员
    members_result = await db.execute(
        select(AlertAggregateMember)
        .where(AlertAggregateMember.group_id == group_id)
        .order_by(AlertAggregateMember.added_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    members = members_result.scalars().all()

    # 获取每个成员的告警详情
    member_alert_ids = [m.alert_id for m in members]
    if member_alert_ids:
        alerts_result = await db.execute(
            select(Alert).where(Alert.id.in_(member_alert_ids))
        )
        alert_map = {a.id: a for a in alerts_result.scalars().all()}
    else:
        alert_map = {}

    items = []
    for m in members:
        a = alert_map.get(m.alert_id)
        if a:
            items.append(AlertAggregateMemberItem(
                alert_id=m.alert_id,
                title=a.title,
                severity=a.severity,
                fired_at=a.fired_at,
                source=a.source,
                status=a.status,
                added_at=m.added_at,
            ))

    return AlertAggregateMembersResponse(
        items=items,
        total=total,
        group_key=group.group_key,
        alert_count=group.alert_count,
        page=page,
        page_size=page_size,
    )


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    request: AlertUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新告警"""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == str(tenant_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 记录历史
    history = AlertHistory(
        tenant_id=str(tenant_id),
        alert_id=alert_id,
        action="update",
        operator_id=current_user.id,
        operator_name=current_user.username,
        old_value={"status": alert.status, "severity": alert.severity},
    )
    db.add(history)

    # 更新字段
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)
    return alert


# ============ 告警诊断 ============

@router.get("/alerts/diagnose/{trace_id}", response_model=DiagnosisResponse)
async def diagnose_alert(
    trace_id: str,
    tenant_id: int = Depends(get_current_tenant_id),
    redis=Depends(get_redis),
):
    """诊断模式 - 根据Trace ID查看告警处理流程"""
    trace_key = f"trace:{trace_id}"
    trace_data = await redis.hgetall(trace_key)

    if not trace_data:
        raise HTTPException(status_code=404, detail="Trace not found")

    if trace_data.get("tenant_id") != str(tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # 获取步骤
    steps_raw = await redis.lrange(f"{trace_key}:steps", 0, -1)
    steps = [json.loads(s) for s in steps_raw]

    # 构建响应
    flow_steps = []
    for i, step in enumerate(steps):
        flow_steps.append(TraceStep(
            step=i + 1,
            type=step.get("type", ""),
            title=_get_step_title(step.get("type", "")),
            description=step.get("data", {}).get("description", ""),
            status=step.get("status", "success"),
            details=step.get("data", {}).get("details"),
            reason=step.get("data", {}).get("reason"),
            time=step.get("time"),
        ))

    # 时间线
    timeline = [
        {"time": s.get("time", ""), "event": _get_step_title(s.get("type", ""))}
        for s in steps
    ]

    return DiagnosisResponse(
        trace_id=trace_id,
        summary={
            "status": trace_data.get("final_status"),
            "deduction_reason": trace_data.get("deduction_reason"),
            "suppress_reason": trace_data.get("suppress_reason"),
        },
        matched_rules=json.loads(trace_data.get("matched_rules", "[]")),
        flow_steps=flow_steps,
        timeline=timeline,
    )


# ============ 云产品指标 ============

@router.get("/cloud-metrics")
async def list_cloud_metrics(
    product: Optional[str] = None,
    namespace: Optional[str] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取云产品指标列表"""
    query = select(CloudProductMetric).where(CloudProductMetric.is_active == 1)

    if product:
        query = query.where(CloudProductMetric.product == product)
    if namespace:
        query = query.where(CloudProductMetric.namespace == namespace)

    result = await db.execute(query.order_by(CloudProductMetric.product, CloudProductMetric.metric_name))
    metrics = result.scalars().all()
    return metrics


@router.get("/cloud-metrics/map")
async def get_metrics_by_namespace(
    namespace: str,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取指定 namespace 下的所有指标"""
    result = await db.execute(
        select(CloudProductMetric).where(
            and_(
                CloudProductMetric.namespace == namespace,
                CloudProductMetric.is_active == 1,
            )
        ).order_by(CloudProductMetric.metric_name)
    )
    metrics = result.scalars().all()
    return {
        "namespace": namespace,
        "metrics": [
            {
                "metric_name": m.metric_name,
                "metric_desc": m.metric_desc,
                "unit": m.unit,
                "dimensions": m.dimensions,
            }
            for m in metrics
        ]
    }


def _get_step_title(step_type: str) -> str:
    """获取步骤标题"""
    titles = {
        "received": "告警接入",
        "fingerprint": "指纹生成",
        "dedup_check": "去重检查",
        "dedup_result": "去重结果",
        "suppress_check": "抑制检查",
        "suppress_result": "抑制结果",
        "aggregate_check": "聚合检查",
        "aggregate_result": "聚合结果",
        "rule_match": "规则匹配",
        "route_result": "路由结果",
        "notification_queued": "进入发送队列",
        "notification_sent": "发送成功",
        "notification_failed": "发送失败",
    }
    return titles.get(step_type, step_type)
