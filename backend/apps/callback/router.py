"""
SentinelX - 回调处理
处理来自外部系统的告警回调
"""
import secrets
import hmac
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.config import settings
from apps.core.database import get_db
from apps.core.security import generate_signature, verify_signature
from apps.alert.models import Alert, AlertHistory
import structlog

logger = structlog.get_logger()

router = APIRouter()


def generate_callback_token(alert_id: int) -> str:
    """生成 HMAC 签名的回调 token"""
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    signature = generate_signature(settings.JWT_SECRET_KEY, timestamp, str(alert_id))
    return f"{timestamp}.{signature}"


def verify_callback_token(alert_id: int, token: str) -> bool:
    """验证 HMAC 签名的回调 token（有效期 24 小时）"""
    parts = token.split(".", 1)
    if len(parts) != 2:
        return False
    timestamp, signature = parts
    # 验证时间戳（24 小时有效期）
    try:
        ts = int(timestamp)
        now = int(datetime.now(timezone.utc).timestamp())
        if now - ts > 86400:
            return False
    except (ValueError, TypeError):
        return False
    return verify_signature(settings.JWT_SECRET_KEY, timestamp, str(alert_id), signature)


def verify_dingtalk_signature(token: str, signature: str, timestamp: str) -> bool:
    """验证钉钉回调签名"""
    if not signature or not timestamp:
        return False
    string_to_sign = f"{timestamp}\n{token}"
    secret_enc = token.encode("utf-8")
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    my_signature = base64.b64encode(hmac_code).decode("utf-8")
    return my_signature == signature



@router.post("/callback/dingtalk")
async def dingtalk_callback(
    challenge: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    钉钉回调URL验证
    钉钉在创建回调URL时会发送一个GET请求来验证URL有效性
    """
    if challenge:
        # URL验证请求
        return {"challenge": challenge}

    # 处理回调
    return {"status": "ok"}


@router.post("/callback/{alert_id}/ack")
async def acknowledge_alert_callback(
    alert_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    确认告警回调
    外部系统（如运维平台）确认处理告警后调用此接口
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 验证 HMAC 签名 token
    if not verify_callback_token(alert.id, token):
        raise HTTPException(status_code=403, detail="Invalid token")

    # 更新告警状态
    old_status = alert.status
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)

    # 记录历史（与状态更新在同一事务中提交）
    history = AlertHistory(
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        action="acknowledge_callback",
        description="通过回调确认告警",
        old_value={"status": old_status},
        new_value={"status": "acknowledged"},
    )
    db.add(history)
    await db.commit()

    logger.info("alert_acknowledged_via_callback", alert_id=alert_id)

    return {"status": "ok", "alert_id": alert_id}


@router.post("/callback/{alert_id}/resolve")
async def resolve_alert_callback(
    alert_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    解决告警回调
    外部系统解决告警后调用此接口
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 验证 HMAC 签名 token
    if not verify_callback_token(alert.id, token):
        raise HTTPException(status_code=403, detail="Invalid token")

    # 更新告警状态
    old_status = alert.status
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)

    # 记录历史（与状态更新在同一事务中提交）
    history = AlertHistory(
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        action="resolve_callback",
        description="通过回调解决告警",
        old_value={"status": "acknowledged"},
        new_value={"status": "resolved"},
    )
    db.add(history)
    await db.commit()

    logger.info("alert_resolved_via_callback", alert_id=alert_id)

    return {"status": "ok", "alert_id": alert_id}


@router.post("/callback/{alert_id}/silence")
async def silence_alert_callback(
    alert_id: int,
    duration_hours: int = Query(24, ge=1, le=720),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    静默告警回调
    临时静默告警一段时间
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # 验证 HMAC 签名 token
    if not verify_callback_token(alert.id, token):
        raise HTTPException(status_code=403, detail="Invalid token")

    # 更新静默时间
    old_status = alert.status
    alert.silenced_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)

    # 记录历史（与静默更新在同一事务中提交）
    history = AlertHistory(
        tenant_id=alert.tenant_id,
        alert_id=alert.id,
        action="silence_callback",
        description=f"通过回调静默告警 {duration_hours} 小时",
        old_value={"status": old_status, "silenced_until": None},
        new_value={"status": old_status, "silenced_until": alert.silenced_until.isoformat()},
    )
    db.add(history)
    await db.commit()

    logger.info("alert_silenced_via_callback", alert_id=alert_id, duration_hours=duration_hours)

    return {"status": "ok", "alert_id": alert_id, "silenced_until": alert.silenced_until.isoformat()}
