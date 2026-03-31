"""
SentinelX - AI路由
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.database import get_db
from apps.auth.routers import get_current_tenant_id
from apps.alert.models import Alert
from apps.ai.service import AIService

router = APIRouter()


@router.post("/alerts/{alert_id}/analyze")
async def analyze_alert(
    alert_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    根因分析
    对指定告警进行AI根因分析
    """
    # 获取告警
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 执行根因分析
    service = AIService()
    analysis, error = await service.analyze_root_cause(alert)

    if error:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {error}")

    return {
        "alert_id": alert_id,
        "analysis": analysis,
    }


@router.post("/alerts/{alert_id}/polish")
async def polish_alert_content(
    alert_id: int,
    template: Optional[str] = None,
    style: str = Query("formal", regex="^(formal|simple|friendly)$"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    内容润色
    将告警内容润色成更易读的通知格式
    """
    # 获取告警
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 执行内容润色
    service = AIService()
    polished, error = await service.polish_content(alert, template, style)

    if error:
        raise HTTPException(status_code=500, detail=f"Polish failed: {error}")

    return {
        "alert_id": alert_id,
        "polished_content": polished,
    }


@router.post("/alerts/{alert_id}/suggest-actions")
async def suggest_alert_actions(
    alert_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    建议操作
    推荐处理该告警的下一步操作
    """
    # 获取告警
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 获取历史告警
    history_result = await db.execute(
        select(Alert).where(
            Alert.tenant_id == tenant_id,
            Alert.alert_key == alert.alert_key,
            Alert.id != alert_id,
        ).order_by(Alert.fired_at.desc()).limit(10)
    )
    history_alerts = history_result.scalars().all()

    history = [
        {
            "title": a.title,
            "status": a.status,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        }
        for a in history_alerts
    ]

    # 执行建议
    service = AIService()
    actions, error = await service.suggest_actions(alert, history)

    if error:
        raise HTTPException(status_code=500, detail=f"Suggestion failed: {error}")

    return {
        "alert_id": alert_id,
        "suggested_actions": actions,
    }


@router.post("/alerts/{alert_id}/predict-impact")
async def predict_alert_impact(
    alert_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    影响预测
    预测告警未处理可能造成的影响
    """
    # 获取告警
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 执行影响预测
    service = AIService()
    impact, error = await service.predict_impact(alert)

    if error:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {error}")

    return {
        "alert_id": alert_id,
        "predicted_impact": impact,
    }
