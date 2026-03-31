"""
SentinelX - 通知路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.database import get_db
from apps.auth.routers import get_current_user, get_current_tenant_id
from apps.notify.models import NotificationRecord
from apps.notify.schemas import NotificationRecordResponse

router = APIRouter()


@router.get("/notifications", response_model=list[NotificationRecordResponse])
async def list_notifications(
    alert_id: int = None,
    status: str = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知记录"""
    query = select(NotificationRecord).where(NotificationRecord.tenant_id == tenant_id)

    if alert_id:
        query = query.where(NotificationRecord.alert_id == alert_id)
    if status:
        query = query.where(NotificationRecord.status == status)

    result = await db.execute(query.order_by(NotificationRecord.created_at.desc()).limit(100))
    return result.scalars().all()
