"""
SentinelX - 告警管理路由
"""
import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
import structlog

from apps.core.database import get_db
from apps.core.redis import get_redis
from apps.auth.routers import get_current_user, get_current_tenant_id
from apps.alert.models import Alert, AlertSource, AlertHistory, AlertTrace
from apps.alert.schemas import (
    AlertCreate, AlertUpdate, AlertResponse, AlertListResponse, AlertFilter, AlertStats,
    AlertSourceCreate, AlertSourceUpdate, AlertSourceResponse,
    AlertHistoryResponse, DiagnosisResponse, TraceStep,
)
from apps.alert.services.dispatcher import AlertDispatcher

logger = structlog.get_logger()
router = APIRouter()


def generate_fingerprint(alert: AlertCreate, tenant_id: str) -> str:
    """生成告警指纹"""
    fp_data = {
        "tenant_id": tenant_id,
        "source": alert.source,
        "alert_key": alert.alert_key,
        "labels": json.dumps(alert.labels, sort_keys=True, default=str),
    }
    fp_json = json.dumps(fp_data, sort_keys=True, default=str)
    return hashlib.sha256(fp_json.encode()).hexdigest()[:16]


def generate_trace_id() -> str:
    """生成12位Trace ID"""
    return str(uuid.uuid4())[:12]


# ============ 告警源管理 ============

@router.get("/sources", response_model=list[AlertSourceResponse])
async def list_sources(
    tenant_id: str = Depends(get_current_tenant_id),
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
    tenant_id: str = Depends(get_current_tenant_id),
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
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


# ============ 告警接入 ============

@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    request: AlertCreate,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """接收告警"""
    trace_id = request.trace_id or generate_trace_id()
    fingerprint = request.fingerprint or generate_fingerprint(request, tenant_id)

    # 创建告警记录
    alert = Alert(
        tenant_id=tenant_id,
        alert_key=request.alert_key,
        fingerprint=fingerprint,
        source=request.source,
        title=request.title,
        content=request.content,
        severity=request.severity,
        status="firing",
        labels=request.labels,
        annotations=request.annotations,
        metric_name=request.metric_name,
        metric_value=request.metric_value,
        raw_data=request.raw_data,
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
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    Webhook方式接收告警
    自动识别数据格式并转换为标准告警
    支持: prometheus, alertmanager, zabbix, aliyun, tencent, custom
    """
    from apps.alert.adapters.base import AdapterFactory

    # 获取适配器
    adapter = AdapterFactory.get_adapter(source_type)

    # 解析告警
    parsed_alert = await adapter.parse(raw_data, tenant_id)

    if not parsed_alert:
        raise HTTPException(status_code=400, detail=f"Unsupported alert format for source: {source_type}")

    # 处理列表格式
    if isinstance(parsed_alert, list):
        results = []
        for alert_data in parsed_alert:
            trace_id = generate_trace_id()
            fingerprint = alert_data.fingerprint or generate_fingerprint(alert_data, tenant_id)

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
                trace_id=trace_id,
                fired_at=datetime.utcnow(),
            )
            db.add(alert)
            await db.flush()

            dispatcher = AlertDispatcher(db, redis)
            background_tasks.add_task(dispatcher.dispatch, alert, trace_id)
            results.append(alert)

        await db.commit()
        return {"received": len(results), "alerts": [{"id": r.id, "trace_id": r.trace_id} for r in results]}
    else:
        trace_id = generate_trace_id()
        fingerprint = parsed_alert.fingerprint or generate_fingerprint(parsed_alert, tenant_id)

        alert = Alert(
            tenant_id=tenant_id,
            alert_key=parsed_alert.alert_key,
            fingerprint=fingerprint,
            source=parsed_alert.source,
            title=parsed_alert.title,
            content=parsed_alert.content,
            severity=parsed_alert.severity,
            status="firing",
            labels=parsed_alert.labels,
            annotations=parsed_alert.annotations,
            metric_name=parsed_alert.metric_name,
            metric_value=parsed_alert.metric_value,
            raw_data=parsed_alert.raw_data,
            trace_id=trace_id,
            fired_at=datetime.utcnow(),
        )
        db.add(alert)
        await db.flush()

        dispatcher = AlertDispatcher(db, redis)
        background_tasks.add_task(dispatcher.dispatch, alert, trace_id)

        await db.commit()
        await db.refresh(alert)
        return {"id": alert.id, "trace_id": alert.trace_id}


@router.post("/alerts/batch")
async def create_alerts_batch(
    alerts: List[AlertCreate],
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """批量接收告警"""
    created_alerts = []
    dispatcher = AlertDispatcher(db, redis)

    for alert_data in alerts:
        trace_id = alert_data.trace_id or generate_trace_id()
        fingerprint = alert_data.fingerprint or generate_fingerprint(alert_data, tenant_id)

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

@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
    keyword: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取告警列表"""
    query = select(Alert).where(Alert.tenant_id == tenant_id)

    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
    if source:
        query = query.where(Alert.source == source)
    if keyword:
        query = query.where(
            or_(
                Alert.title.ilike(f"%{keyword}%"),
                Alert.content.ilike(f"%{keyword}%")
            )
        )
    if start_time:
        query = query.where(Alert.fired_at >= start_time)
    if end_time:
        query = query.where(Alert.fired_at <= end_time)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
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
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取告警统计"""
    base_query = select(Alert).where(Alert.tenant_id == tenant_id)

    async def count_by(filter_func):
        result = await db.execute(select(func.count()).select_from(base_query.subquery().where(filter_func)))
        return result.scalar()

    return AlertStats(
        total=await count_by(True),
        firing=await count_by(Alert.status == "firing"),
        resolved=await count_by(Alert.status == "resolved"),
        suppressed=await count_by(Alert.status == "suppressed"),
        critical=await count_by(Alert.status == "firing" and Alert.severity == "critical"),
        high=await count_by(Alert.status == "firing" and Alert.severity == "high"),
        medium=await count_by(Alert.status == "firing" and Alert.severity == "medium"),
        low=await count_by(Alert.status == "firing" and Alert.severity == "low"),
        info=await count_by(Alert.status == "firing" and Alert.severity == "info"),
        unassigned=await count_by(Alert.status == "firing" and Alert.assignee_id == None),
    )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取告警详情"""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    request: AlertUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新告警"""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 记录历史
    history = AlertHistory(
        tenant_id=tenant_id,
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
    tenant_id: str = Depends(get_current_tenant_id),
    redis=Depends(get_redis),
):
    """诊断模式 - 根据Trace ID查看告警处理流程"""
    trace_key = f"trace:{trace_id}"
    trace_data = await redis.hgetall(trace_key)

    if not trace_data:
        raise HTTPException(status_code=404, detail="Trace not found")

    if trace_data.get("tenant_id") != tenant_id:
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
