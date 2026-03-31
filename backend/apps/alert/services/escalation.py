"""
SentinelX - 升级服务
处理告警升级逻辑
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.alert.models import Alert, AlertHistory
from apps.rule.models import AlertRule
from apps.notify.channels import ChannelFactory

logger = structlog.get_logger()


class EscalationService:
    """升级服务"""

    # 升级等待时间配置（分钟）
    ESCALATION_WAITS = {
        0: 5,    # 第0级等待5分钟
        1: 10,   # 第1级等待10分钟
        2: 30,   # 第2级等待30分钟
        3: 60,   # 第3级等待60分钟
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_escalations(self) -> Dict[str, Any]:
        """
        检查并处理需要升级的告警
        返回: {escalated_count, notifications_sent, errors}
        """
        stats = {
            "escalated_count": 0,
            "notifications_sent": 0,
            "errors": [],
        }

        # 查找触发中且未确认的告警
        result = await self.db.execute(
            select(Alert).where(
                Alert.status == "firing",
                Alert.acknowledged_at.is_(None),
                Alert.escalation_count < 4,  # 最多升级4次
            )
        )
        alerts = result.scalars().all()

        for alert in alerts:
            try:
                should_escalate, wait_minutes = await self._should_escalate(alert)
                if should_escalate:
                    await self._escalate_alert(alert)
                    stats["escalated_count"] += 1
            except Exception as e:
                logger.error("escalation_check_error", alert_id=alert.id, error=str(e))
                stats["errors"].append({"alert_id": alert.id, "error": str(e)})

        return stats

    async def _should_escalate(self, alert: Alert) -> tuple[bool, int]:
        """判断告警是否应该升级"""
        if alert.escalation_count >= len(self.ESCALATION_WAITS):
            return False, 0

        wait_minutes = self.ESCALATION_WAITS.get(alert.escalation_count, 60)
        last_notification = await self._get_last_notification_time(alert)

        if last_notification:
            # 检查距离上次通知是否超过等待时间
            elapsed = (datetime.utcnow() - last_notification).total_seconds() / 60
            if elapsed < wait_minutes:
                return False, wait_minutes - elapsed

        # 检查告警触发时间
        if alert.fired_at:
            elapsed_since_fire = (datetime.utcnow() - alert.fired_at).total_seconds() / 60
            expected_wait = sum(self.ESCALATION_WAITS.get(i, 60) for i in range(alert.escalation_count + 1))
            if elapsed_since_fire < expected_wait:
                return False, expected_wait - elapsed_since_fire

        return True, wait_minutes

    async def _get_last_notification_time(self, alert: Alert) -> datetime:
        """获取告警最后一次通知时间"""
        result = await self.db.execute(
            select(AlertHistory).where(
                AlertHistory.alert_id == alert.id,
                AlertHistory.action.like("%notification%")
            ).order_by(AlertHistory.created_at.desc()).limit(1)
        )
        history = result.scalar_one_or_none()
        return history.created_at if history else None

    async def _escalate_alert(self, alert: Alert):
        """执行告警升级"""
        # 更新升级计数
        alert.escalation_count += 1

        # 记录历史
        history = AlertHistory(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            action=f"escalate_level_{alert.escalation_count}",
            description=f"告警升级至第 {alert.escalation_count} 级",
            old_value={"escalation_count": alert.escalation_count - 1},
            new_value={"escalation_count": alert.escalation_count},
        )
        self.db.add(history)

        # 获取匹配的规则并重新发送通知
        # 实际应该获取升级通知渠道配置
        logger.info(
            "alert_escalated",
            alert_id=alert.id,
            escalation_count=alert.escalation_count,
            title=alert.title,
        )

        await self.db.commit()

    async def get_escalation_candidates(self) -> List[Alert]:
        """获取可能需要升级的告警列表"""
        result = await self.db.execute(
            select(Alert).where(
                Alert.status == "firing",
                Alert.acknowledged_at.is_(None),
            ).order_by(Alert.escalation_count, Alert.fired_at)
        )
        return result.scalars().all()

    async def auto_assign(self, alert: Alert, user_id: int, user_name: str):
        """自动指派告警"""
        old_assignee_id = alert.assignee_id
        old_assignee_name = alert.assignee_name

        alert.assignee_id = user_id
        alert.assignee_name = user_name

        # 记录历史
        history = AlertHistory(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            action="auto_assign",
            description=f"自动指派给 {user_name}",
            operator_id=user_id,
            operator_name=user_name,
            old_value={"assignee_id": old_assignee_id, "assignee_name": old_assignee_name},
            new_value={"assignee_id": user_id, "assignee_name": user_name},
        )
        self.db.add(history)
        await self.db.commit()

        logger.info("alert_auto_assigned", alert_id=alert.id, user_id=user_id, user_name=user_name)


class EscalationWorker:
    """升级Worker - 定期检查并升级告警"""

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds

    async def run(self):
        """运行Worker"""
        import asyncio
        from apps.core.database import async_session_factory

        while True:
            try:
                async with async_session_factory() as db:
                    service = EscalationService(db)
                    stats = await service.check_escalations()
                    if stats["escalated_count"] > 0:
                        logger.info(
                            "escalation_cycle_completed",
                            escalated=stats["escalated_count"],
                            notifications=stats["notifications_sent"],
                        )
            except Exception as e:
                logger.error("escalation_worker_error", error=str(e))

            await asyncio.sleep(self.check_interval)
