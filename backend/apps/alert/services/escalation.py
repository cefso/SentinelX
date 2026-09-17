"""
SentinelX - 升级服务
处理告警升级逻辑
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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

    # 单次扫描批量上限，避免全表 firing 一次性载入
    DEFAULT_BATCH_SIZE = 500

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_escalations(
        self,
        tenant_id: Optional[int] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        lookback_hours: Optional[int] = 24,
    ) -> Dict[str, Any]:
        """
        检查并处理需要升级的告警
        tenant_id: 可选，限定只扫描该租户（手动触发时必须传入）
        batch_size: 单次扫描告警上限
        lookback_hours: 仅扫描最近 N 小时触发的告警；None 表示不限
        返回: {escalated_count, notifications_sent, errors}
        """
        stats = {
            "escalated_count": 0,
            "notifications_sent": 0,
            "errors": [],
        }

        # 查找触发中且未确认的告警（分批 + 可选时间窗）
        query = select(Alert).where(
            Alert.status == "firing",
            Alert.acknowledged_at.is_(None),
            Alert.escalation_count < 4,  # 最多升级4次
        )
        if tenant_id is not None:
            query = query.where(Alert.tenant_id == tenant_id)
        if lookback_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            query = query.where(Alert.fired_at >= cutoff)
        query = query.order_by(Alert.fired_at.asc()).limit(batch_size)

        result = await self.db.execute(query)
        alerts = list(result.scalars().all())
        if not alerts:
            return stats

        # 一条查询批量取每个 alert 的最后通知时间，消除 per-alert N+1
        last_notify_map = await self._get_last_notification_times(
            [a.id for a in alerts]
        )

        escalated_any = False
        for alert in alerts:
            try:
                should_escalate, wait_minutes = self._should_escalate(
                    alert,
                    last_notification=last_notify_map.get(alert.id),
                )
                if should_escalate:
                    await self._escalate_alert(alert, commit=False)
                    escalated_any = True
                    stats["escalated_count"] += 1
            except Exception as e:
                logger.error("escalation_check_error", alert_id=alert.id, error=str(e))
                stats["errors"].append({"alert_id": alert.id, "error": str(e)})

        # 批量升级后一次 commit
        if escalated_any:
            await self.db.commit()

        return stats

    def _should_escalate(
        self,
        alert: Alert,
        last_notification: Optional[datetime] = None,
    ) -> tuple[bool, int]:
        """判断告警是否应该升级（last_notification 需由调用方预加载）"""
        if alert.escalation_count >= len(self.ESCALATION_WAITS):
            return False, 0

        wait_minutes = self.ESCALATION_WAITS.get(alert.escalation_count, 60)

        if last_notification:
            # 检查距离上次通知是否超过等待时间
            elapsed = (datetime.now(timezone.utc) - last_notification).total_seconds() / 60
            if elapsed < wait_minutes:
                return False, wait_minutes - elapsed

        # 检查告警触发时间
        if alert.fired_at:
            elapsed_since_fire = (datetime.now(timezone.utc) - alert.fired_at).total_seconds() / 60
            expected_wait = sum(self.ESCALATION_WAITS.get(i, 60) for i in range(alert.escalation_count + 1))
            if elapsed_since_fire < expected_wait:
                return False, expected_wait - elapsed_since_fire

        return True, wait_minutes

    async def _get_last_notification_times(
        self,
        alert_ids: List[int],
    ) -> Dict[int, datetime]:
        """批量获取告警最后通知时间：一条 GROUP BY 查询"""
        if not alert_ids:
            return {}

        result = await self.db.execute(
            select(
                AlertHistory.alert_id,
                func.max(AlertHistory.created_at).label("last_at"),
            )
            .where(
                AlertHistory.alert_id.in_(alert_ids),
                AlertHistory.action.like("%notification%"),
            )
            .group_by(AlertHistory.alert_id)
        )
        return {row.alert_id: row.last_at for row in result.all()}

    async def _get_last_notification_time(self, alert: Alert) -> Optional[datetime]:
        """获取告警最后一次通知时间（单条路径）"""
        result = await self._get_last_notification_times([alert.id])
        return result.get(alert.id)

    async def _escalate_alert(self, alert: Alert, commit: bool = True):
        """执行告警升级"""
        old_count = alert.escalation_count
        alert.escalation_count += 1

        # 记录历史
        history = AlertHistory(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            action="escalated",
            description=f"告警升级至第 {alert.escalation_count} 级",
            old_value={"escalation_count": old_count},
            new_value={"escalation_count": alert.escalation_count},
        )
        self.db.add(history)

        logger.info(
            "alert_escalated",
            alert_id=alert.id,
            escalation_count=alert.escalation_count,
            title=alert.title,
        )

        if commit:
            await self.db.commit()

    async def get_escalation_candidates(self, tenant_id: Optional[int] = None) -> List[Alert]:
        """获取可能需要升级的告警列表（可选按租户过滤）"""
        query = select(Alert).where(
            Alert.status == "firing",
            Alert.acknowledged_at.is_(None),
        )
        if tenant_id is not None:
            query = query.where(Alert.tenant_id == tenant_id)
        query = query.order_by(Alert.escalation_count, Alert.fired_at)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def check_and_escalate(self, alert_id: int) -> bool:
        """根据 MQ 消息检查并执行升级"""
        result = await self.db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()

        if not alert:
            return False

        # 若告警已确认或已解决，跳过
        if alert.acknowledged_at or alert.status != "firing":
            return False

        current_level = alert.escalation_count or 0
        if current_level >= 4:
            return False  # 已达最高级别

        # 检查是否应该升级（单条路径仍查一次 last notification）
        last_notification = await self._get_last_notification_time(alert)
        should_escalate, wait_minutes = self._should_escalate(
            alert, last_notification=last_notification
        )
        if should_escalate:
            await self._escalate_alert(alert)

            # 发送下一个级别的检查消息
            next_level = current_level + 1
            if next_level < 4:
                from apps.core.mq import get_mq_async
                mq = await get_mq_async()
                await mq.send("alerts_escalation", {
                    "alert_id": alert.id,
                    "tenant_id": alert.tenant_id,
                    "action": "check_escalation",
                    "level": next_level
                })

        return True

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
            action="updated",
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
    """升级 Worker - 通过 MQ 事件驱动，而非轮询"""

    # 升级等待时间配置（秒）
    ESCALATION_WAITS_S = {
        0: 300,   # 第0级等待5分钟
        1: 600,   # 第1级等待10分钟
        2: 1800,  # 第2级等待30分钟
        3: 3600,  # 第3级等待60分钟
    }

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds

    async def run(self):
        """运行 Worker - 消费 MQ 消息"""
        from apps.core.mq import get_mq_async
        from apps.core.database import AsyncSessionLocal as async_session_factory

        mq = await get_mq_async()
        logger.info("escalation_worker_started")

        backoff = 1  # 指数退避起始值（秒）
        max_backoff = 30  # 最大退避时间
        msg = None

        while True:
            try:
                msg = await mq.receive("alerts_escalation", count=1)
                if not msg:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                    continue

                # 收到消息，重置退避
                backoff = 1

                message = msg.message
                alert_id = message.get("alert_id")

                async with async_session_factory() as db:
                    service = EscalationService(db)
                    await service.check_and_escalate(alert_id)

                await mq.ack("alerts_escalation", msg.msg_id)

            except Exception as e:
                logger.error("escalation_worker_error", error=str(e))
                if msg:
                    await mq.nack("alerts_escalation", msg.msg_id, vt=60)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
