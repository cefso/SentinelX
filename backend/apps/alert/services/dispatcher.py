"""
SentinelX - 告警分发器
核心处理流程：接入 → 规则引擎处理(去重/抑制/聚合/匹配) → 通知队列
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from apps.alert.models import Alert, AlertHistory, AlertTrace
from apps.rule.models import AlertRule, NotificationChannel
from apps.rule.engine import RuleEngine
from apps.core.database import AsyncSessionLocal
from apps.core.mq import get_mq_async

logger = structlog.get_logger()


class AlertDispatcher:
    """
    告警分发器 - 协调各处理模块
    """

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.rule_engine = RuleEngine()

    async def dispatch(self, alert: Alert, trace_id: str):
        """主分发流程"""
        try:
            # 初始化Trace
            await self._init_trace(alert, trace_id)

            # 调用规则引擎统一处理（去重/抑制/聚合/匹配）
            result = await self.rule_engine.process_alert(
                self.db, self.redis, alert, trace_id,
                add_trace_step=self._add_trace_step
            )

            # 根据结果处理
            if result.is_suppressed:
                await self._handle_suppressed(alert, trace_id, result.suppress_reason)
                return

            if result.is_duplicate:
                # 重复告警，记录但不创建新告警
                await self._finish_trace(trace_id, "duplicate")
                return

            # 记录匹配的规则信息到告警
            if result.matched_rules:
                alert.matched_rules = [
                    {"id": r.id, "name": r.name, "priority": r.priority, "actions": r.actions or []}
                    for r in result.matched_rules
                ]

            # 创建/更新告警记录
            await self._finalize_alert(alert, result.matched_rules, result.channel_ids, result.aggregated_info, trace_id)

            # 进入通知队列
            await self._queue_notification(alert, result.matched_rules, result.channel_ids, result.template_map, trace_id)

            # 发送升级检查消息
            try:
                mq = await get_mq_async()
                await mq.send("alerts_escalation", {
                    "alert_id": alert.id,
                    "tenant_id": alert.tenant_id,
                    "action": "check_escalation",
                    "level": 0
                })
            except Exception as e:
                logger.warning("escalation_msg_send_failed", alert_id=alert.id, error=str(e))

            logger.info("alert_dispatched", alert_id=alert.id, trace_id=trace_id)

        except Exception as e:
            logger.error("dispatch_error", alert_id=alert.id, trace_id=trace_id, error=str(e))
            await self._handle_error(alert, trace_id, str(e))

    async def _init_trace(self, alert: Alert, trace_id: str):
        """初始化追踪记录"""
        trace_key = f"trace:{trace_id}"
        trace_data = {
            "trace_id": str(trace_id),
            "alert_id": str(alert.id),
            "tenant_id": str(alert.tenant_id),
            "start_time": str(datetime.now(timezone.utc).isoformat()),
            "final_status": "processing",
        }
        await self.redis.hset(trace_key, mapping=trace_data)
        await self.redis.expire(trace_key, 86400 * 7)  # 7天
        await self._add_trace_step(trace_id, "received", "告警接入", "success", {
            "source": str(alert.source),
            "severity": str(alert.severity),
            "alert_key": str(alert.alert_key),
        })

    async def _handle_suppressed(self, alert: Alert, trace_id: str, reason: str):
        """处理被抑制的告警"""
        alert.status = "suppressed"
        await self.db.commit()

        await self._finish_trace(trace_id, "suppressed", suppress_reason=reason)

    async def _finalize_alert(
        self,
        alert: Alert,
        matched_rules: List[AlertRule],
        channel_ids: List[int],
        aggregated_info: Optional[Dict],
        trace_id: str
    ):
        """完成告警处理"""
        # 检查是否为 OK 恢复消息（阿里云云监控1.0）
        alert_state = alert.annotations.get("alert_state") if alert.annotations else None
        if alert_state == "OK":
            alert.status = "resolved"
            alert.fire_count = 1
            alert.notification_channels = channel_ids
            # 记录恢复历史
            history = AlertHistory(
                tenant_id=alert.tenant_id,
                alert_id=alert.id,
                action="resolved",
                description="阿里云云监控告警恢复",
                new_value={"status": "resolved", "alert_state": "OK"},
            )
            self.db.add(history)
            await self.db.commit()
            return

        alert.status = "firing"
        alert.fire_count = 1
        alert.notification_channels = channel_ids

        # 记录历史
        history = AlertHistory(
            tenant_id=alert.tenant_id,
            alert_id=alert.id,
            action="fired",
            description="告警触发",
            new_value={"status": "firing", "matched_rules": len(matched_rules)},
        )
        self.db.add(history)
        await self.db.commit()

    async def _queue_notification(
        self,
        alert: Alert,
        matched_rules: List[AlertRule],
        channel_ids: List[int],
        template_map: Dict[int, int | None],
        trace_id: str
    ):
        """进入通知队列"""
        used_fallback = False

        if not channel_ids:
            # 查询默认通知渠道作为兜底
            result = await self.db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.tenant_id == alert.tenant_id,
                    NotificationChannel.is_active == True,
                    NotificationChannel.is_default == True,
                ).limit(1)
            )
            default_channel = result.scalar_one_or_none()
            if default_channel:
                channel_ids = [default_channel.id]
                used_fallback = True
                await self._add_trace_step(trace_id, "notification_queued", "通知队列", "fallback", {
                    "description": f"无匹配规则，使用默认渠道: {default_channel.name}",
                    "channel_id": default_channel.id,
                    "channel_name": default_channel.name,
                })
            else:
                await self._add_trace_step(trace_id, "notification_queued", "通知队列", "skipped", {
                    "description": "无匹配通知渠道，跳过通知",
                })
                await self._finish_trace(trace_id, "no_channels")
                return

        # 通知去重：检查是否在最近时间窗口内已经发送过通知
        # 使用 fingerprint 作为去重键，同一告警只通知一次
        notify_dedup_key = f"notified:{alert.tenant_id}:{alert.fingerprint}"
        notify_window_seconds = 60  # 60秒去重窗口

        already_notified = await self.redis.get(notify_dedup_key)
        if already_notified:
            # redis.get returns bytes in some cases, decode to string
            previous_id = already_notified.decode() if isinstance(already_notified, bytes) else str(already_notified)
            await self._add_trace_step(trace_id, "notification_queued", "通知队列", "dedup_skipped", {
                "description": f"去重跳过，{notify_window_seconds}秒内已通知",
                "fingerprint": str(alert.fingerprint),
                "previous_alert_id": previous_id,
            })
            await self._finish_trace(trace_id, "dedup_skipped")
            return

        # 构建通知消息
        # Convert template_map keys to strings for JSON serialization
        template_map_str_keys = {str(k): v for k, v in template_map.items()} if template_map else {}
        notification_msg = {
            "alert_id": int(alert.id),
            "trace_id": str(trace_id),
            "tenant_id": str(alert.tenant_id),
            "title": str(alert.title) if alert.title else "",
            "content": str(alert.content) if alert.content else "",
            "severity": str(alert.severity),
            "channels": [int(c) for c in channel_ids],
            "template_map": template_map_str_keys,
            "labels": alert.labels or {},
            "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
        }

        # 写入 PGMQ 队列
        mq = await get_mq_async()
        await mq.send("alerts_notify", notification_msg)

        # 设置去重键，标记已通知
        await self.redis.set(notify_dedup_key, str(alert.id), ex=notify_window_seconds)

        # 只有在非fallback情况下才添加成功步骤
        if not used_fallback:
            await self._add_trace_step(trace_id, "notification_queued", "通知队列", "success", {
                "description": f"已加入通知队列，共 {len(channel_ids)} 个渠道",
            })

        await self._finish_trace(trace_id, "queued")

    async def _handle_error(self, alert: Alert, trace_id: str, error: str):
        """处理错误"""
        alert.status = "firing"  # 保持触发状态
        await self.db.commit()
        await self._finish_trace(trace_id, "failed", error_reason=error)

    async def _finish_trace(self, trace_id: str, status: str, **kwargs):
        """完成追踪 - 持久化到 PG 并更新 Redis"""
        trace_key = f"trace:{trace_id}"

        # 从 Redis 获取完整数据并持久化到 PostgreSQL
        trace_data_raw = await self.redis.hgetall(trace_key)
        if trace_data_raw:
            trace_data = {
                k.decode("utf-8") if isinstance(k, bytes) else k:
                v.decode("utf-8") if isinstance(v, bytes) else v
                for k, v in trace_data_raw.items()
            }

            # 获取步骤链
            steps_raw = await self.redis.lrange(f"{trace_key}:steps", 0, -1)
            steps = [
                json.loads(s.decode("utf-8") if isinstance(s, bytes) else s)
                for s in steps_raw
            ]

            # 持久化到 PostgreSQL
            try:
                alert_trace = AlertTrace(
                    trace_id=trace_id,
                    alert_id=trace_data.get("alert_id"),
                    tenant_id=trace_data.get("tenant_id"),
                    final_status=status,
                    deduction_reason=kwargs.get("deduction_reason"),
                    suppress_reason=kwargs.get("suppress_reason"),
                    matched_rules=json.loads(trace_data.get("matched_rules", "[]")),
                    notification_channels=json.loads(trace_data.get("notification_channels", "[]")),
                    steps_chain=steps,
                    expired_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
                self.db.add(alert_trace)
                await self.db.commit()
                logger.info("trace_persisted_to_pg", trace_id=trace_id, status=status)
            except Exception as e:
                logger.error("trace_persist_failed", trace_id=trace_id, error=str(e))
                await self.db.rollback()

        # 更新 Redis 状态
        update_data = {"final_status": str(status)}
        for k, v in kwargs.items():
            update_data[str(k)] = str(v) if v is not None else ""
        await self.redis.hset(trace_key, mapping=update_data)

    async def _add_trace_step(
        self,
        trace_id: str,
        step_type: str,
        title: str,
        status: str,
        data: dict
    ):
        """添加追踪步骤"""
        trace_key = f"trace:{trace_id}"
        # Ensure all data values are JSON serializable (strings)
        serializable_data = {}
        for k, v in data.items():
            if isinstance(v, (int, float, bool, type(None))):
                serializable_data[str(k)] = str(v)
            elif isinstance(v, bytes):
                serializable_data[str(k)] = v.decode()
            else:
                serializable_data[str(k)] = str(v)
        step = {
            "type": str(step_type),
            "title": str(title),
            "status": str(status),
            "data": serializable_data,
            "time": datetime.now(timezone.utc).isoformat(),
        }
        await self.redis.rpush(f"{trace_key}:steps", json.dumps(step))

    async def start_consumer(self, mq):
        """启动告警消费 Consumer（替代 BackgroundTasks）"""
        msg = None
        while True:
            try:
                msg = await mq.receive("alerts_raw", count=1, vt=60)
                if not msg:
                    continue
                # msg 是 pgmq 的 Message 对象，有 msg_id 和 message 属性
                message = msg.message
                alert_id = message.get("alert_id")
                trace_id = message.get("trace_id")

                if not alert_id:
                    await mq.ack("alerts_raw", msg.msg_id)
                    continue

                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Alert).where(Alert.id == alert_id))
                    alert = result.scalar_one_or_none()
                    if not alert:
                        await mq.ack("alerts_raw", msg.msg_id)
                        continue

                    # 重新获取 Redis 连接
                    from apps.core.redis import get_redis
                    redis = await get_redis()
                    dispatcher = AlertDispatcher(db, redis)
                    await dispatcher.dispatch(alert, trace_id)
                    await mq.ack("alerts_raw", msg.msg_id)
            except Exception as e:
                logger.error("alert_consumer_error", error=str(e))
                if msg:
                    await mq.nack("alerts_raw", msg.msg_id, vt=60)
                await asyncio.sleep(1)
