"""
SentinelX - 告警升级路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.core.database import get_db
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.tenant.models import User
from apps.alert.services.escalation import EscalationService

router = APIRouter()


@router.get("/alerts/escalation/candidates")
async def list_escalation_candidates(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取待升级告警列表
    列出所有触发中且未确认的告警（可能需要升级）
    """
    service = EscalationService(db)
    alerts = await service.get_escalation_candidates()
    return {
        "total": len(alerts),
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "severity": a.severity,
                "status": a.status,
                "fired_at": a.fired_at.isoformat() if a.fired_at else None,
                "escalation_count": a.escalation_count,
                "assignee_id": a.assignee_id,
                "assignee_name": a.assignee_name,
            }
            for a in alerts
            if a.tenant_id == str(tenant_id)
        ],
    }


@router.post("/alerts/{alert_id}/escalate")
async def manual_escalate(
    alert_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动升级告警
    立即将告警提升一级，触发升级通知
    """
    from sqlalchemy import select
    from apps.alert.models import Alert, AlertHistory

    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.tenant_id == str(tenant_id))
    )
    alert = result.scalar_one_or_none()

    if not alert:
        return {"success": False, "message": "Alert not found"}

    if alert.status != "firing":
        return {"success": False, "message": "Only firing alerts can be escalated"}

    service = EscalationService(db)
    await service._escalate_alert(alert)

    # 手动触发升级通知
    from apps.notify.services.sender import NotificationService
    from apps.core.redis import RedisClient
    redis = await RedisClient.get_instance()
    sender = NotificationService(db)
    channel_ids = alert.notification_channels or []
    if channel_ids:
        await sender.send_alert_notifications(alert, channel_ids, alert.trace_id)

    return {
        "success": True,
        "message": f"Alert escalated to level {alert.escalation_count}",
        "escalation_count": alert.escalation_count,
    }


@router.post("/alerts/escalation/check")
async def run_escalation_check(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动触发升级检查
    扫描所有告警，执行升级逻辑（供定时任务或手动调用）
    """
    service = EscalationService(db)
    stats = await service.check_escalations()
    return {
        "success": True,
        "stats": stats,
    }
