"""
SentinelX - 告警分发器
核心处理流程：接入 → 去重 → 抑制 → 聚合 → 规则匹配 → 通知
"""
import json
from datetime import datetime
from typing import Optional, List
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from redis.asyncio import Redis

from apps.alert.models import Alert, AlertRule, AlertTrace
from apps.rule.engine import RuleEngine

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

            # 1. 去重检查
            is_duplicate = await self._check_dedup(alert, trace_id)
            if is_duplicate:
                await self._handle_duplicate(alert, trace_id)
                return

            # 2. 抑制检查
            is_suppressed, suppress_reason = await self._check_suppress(alert, trace_id)
            if is_suppressed:
                await self._handle_suppressed(alert, trace_id, suppress_reason)
                return

            # 3. 聚合检查
            aggregated = await self._check_aggregate(alert, trace_id)

            # 4. 规则匹配
            matched_rules = await self._match_rules(alert, trace_id)

            # 5. 创建/更新告警记录
            await self._finalize_alert(alert, matched_rules, trace_id)

            # 6. 进入通知队列
            await self._queue_notification(alert, matched_rules, trace_id)

            # 7. AI分析 (如果启用)
            # await self._trigger_ai_analysis(alert)

            logger.info("alert_dispatched", alert_id=alert.id, trace_id=trace_id)

        except Exception as e:
            logger.error("dispatch_error", alert_id=alert.id, trace_id=trace_id, error=str(e))
            await self._handle_error(alert, trace_id, str(e))

    async def _init_trace(self, alert: Alert, trace_id: str):
        """初始化追踪记录"""
        trace_key = f"trace:{trace_id}"
        trace_data = {
            "trace_id": trace_id,
            "alert_id": str(alert.id),
            "tenant_id": alert.tenant_id,
            "start_time": datetime.utcnow().isoformat(),
            "final_status": "processing",
        }
        await self.redis.hset(trace_key, mapping=trace_data)
        await self.redis.expire(trace_key, 86400 * 7)  # 7天
        await self._add_trace_step(trace_id, "received", "告警接入", "success", {
            "source": alert.source,
            "severity": alert.severity,
            "alert_key": alert.alert_key,
        })

    async def _check_dedup(self, alert: Alert, trace_id: str) -> bool:
        """去重检查"""
        await self._add_trace_step(trace_id, "dedup_check", "去重检查", "processing", {
            "fingerprint": alert.fingerprint
        })

        # 基于指纹的去重检查
        dedup_key = f"dedup:{alert.tenant_id}:{alert.fingerprint}"
        exists = await self.redis.exists(dedup_key)

        if exists:
            await self._add_trace_step(trace_id, "dedup_result", "去重结果", "skipped", {
                "description": "发现重复告警",
                "fingerprint": alert.fingerprint,
            })
            return True

        # 标记为已处理
        await self.redis.setex(dedup_key, 300, str(alert.id))  # 5分钟窗口
        await self._add_trace_step(trace_id, "dedup_result", "去重结果", "passed", {
            "description": "无重复，新告警",
        })
        return False

    async def _handle_duplicate(self, alert: Alert, trace_id: str):
        """处理重复告警"""
        alert.fire_count += 1
        alert.repeat_count += 1
        await self.db.commit()

        await self._finish_trace(trace_id, "duplicate", deduction_reason="相同指纹告警在5分钟内已存在")

    async def _check_suppress(self, alert: Alert, trace_id: str) -> tuple[bool, Optional[str]]:
        """抑制检查"""
        await self._add_trace_step(trace_id, "suppress_check", "抑制检查", "processing", {})

        # TODO: 实现维护期检查、依赖抑制等
        # 检查是否处于维护窗口

        await self._add_trace_step(trace_id, "suppress_result", "抑制检查", "passed", {
            "description": "未触发抑制",
        })
        return False, None

    async def _handle_suppressed(self, alert: Alert, trace_id: str, reason: str):
        """处理被抑制的告警"""
        alert.status = "suppressed"
        await self.db.commit()

        await self._finish_trace(trace_id, "suppressed", suppress_reason=reason)

    async def _check_aggregate(self, alert: Alert, trace_id: str) -> bool:
        """聚合检查"""
        await self._add_trace_step(trace_id, "aggregate_check", "聚合检查", "processing", {})

        # TODO: 实现基于时间窗口和标签的聚合
        # 如果满足聚合条件，返回True并更新原聚合告警

        await self._add_trace_step(trace_id, "aggregate_result", "聚合检查", "skipped", {
            "description": "未触发聚合",
        })
        return False

    async def _match_rules(self, alert: Alert, trace_id: str) -> List[AlertRule]:
        """规则匹配"""
        await self._add_trace_step(trace_id, "rule_match", "规则匹配", "processing", {})

        # 准备告警数据
        alert_data = {
            "severity": alert.severity,
            "source": alert.source,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
        }

        matched_rules = await self.rule_engine.match(alert.tenant_id, alert_data)

        matched_rules_info = [
            {"id": r.id, "name": r.name, "priority": r.priority}
            for r in matched_rules
        ]

        await self._add_trace_step(trace_id, "rule_match", "规则匹配", "success", {
            "description": f"匹配到 {len(matched_rules)} 条规则",
            "matched_rules": matched_rules_info,
        })

        # 更新告警的匹配规则
        alert.matched_rules = matched_rules_info

        return matched_rules

    async def _finalize_alert(self, alert: Alert, matched_rules: List[AlertRule], trace_id: str):
        """完成告警处理"""
        alert.status = "firing"
        alert.fire_count = 1
        await self.db.commit()

    async def _queue_notification(self, alert: Alert, matched_rules: List[AlertRule], trace_id: str):
        """进入通知队列"""
        await self._add_trace_step(trace_id, "notification_queued", "进入发送队列", "success", {
            "description": "告警已加入通知队列",
            "rule_count": len(matched_rules),
        })

        # TODO: 写入PGMQ通知队列
        # from apps.core.mq import get_mq_async
        # mq = await get_mq_async()
        # await mq.send("alerts_notify", {
        #     "alert_id": alert.id,
        #     "trace_id": trace_id,
        #     "channels": [r.actions for r in matched_rules],
        # })

        await self._finish_trace(trace_id, "queued")

    async def _handle_error(self, alert: Alert, trace_id: str, error: str):
        """处理错误"""
        alert.status = "firing"  # 保持触发状态
        await self.db.commit()
        await self._finish_trace(trace_id, "failed", deduction_reason=error)

    async def _finish_trace(self, trace_id: str, status: str, **kwargs):
        """完成追踪"""
        trace_key = f"trace:{trace_id}"
        update_data = {"final_status": status}
        update_data.update(kwargs)
        await self.redis.hset(trace_key, mapping=update_data)

    async def _add_trace_step(self, trace_id: str, step_type: str, title: str, status: str, data: dict):
        """添加追踪步骤"""
        trace_key = f"trace:{trace_id}"
        step = {
            "type": step_type,
            "title": title,
            "status": status,
            "data": data,
            "time": datetime.utcnow().isoformat(),
        }
        await self.redis.rpush(f"{trace_key}:steps", json.dumps(step))
