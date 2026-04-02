"""
SentinelX - 告警分发器
核心处理流程：接入 → 去重 → 抑制 → 聚合 → 规则匹配 → 通知
"""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from redis.asyncio import Redis

from apps.alert.models import Alert, AlertTrace, AlertHistory
from apps.rule.models import AlertRule
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
            is_duplicate, dedup_reason = await self._check_dedup(alert, trace_id)
            if is_duplicate:
                await self._handle_duplicate(alert, trace_id, dedup_reason)
                return

            # 2. 抑制检查
            is_suppressed, suppress_reason = await self._check_suppress(alert, trace_id)
            if is_suppressed:
                await self._handle_suppressed(alert, trace_id, suppress_reason)
                return

            # 3. 聚合检查
            aggregated_info = await self._check_aggregate(alert, trace_id)

            # 4. 规则匹配
            matched_rules, channel_ids = await self._match_rules(alert, trace_id)

            # 5. 创建/更新告警记录
            await self._finalize_alert(alert, matched_rules, channel_ids, aggregated_info, trace_id)

            # 6. 进入通知队列
            await self._queue_notification(alert, matched_rules, channel_ids, trace_id)

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

    async def _check_dedup(self, alert: Alert, trace_id: str) -> tuple[bool, Optional[str]]:
        """去重检查 - 使用Redis实现"""
        await self._add_trace_step(trace_id, "dedup_check", "去重检查", "processing", {
            "fingerprint": alert.fingerprint
        })

        # 基于指纹的去重检查
        dedup_key = f"dedup:{alert.tenant_id}:{alert.fingerprint}"
        dedup_window = 300  # 5分钟窗口

        # 使用SET NX实现原子性检查
        is_new = await self.redis.set(dedup_key, str(alert.id), nx=True, ex=dedup_window)

        if is_new:
            await self._add_trace_step(trace_id, "dedup_result", "去重检查", "passed", {
                "description": "新告警，无重复",
                "fingerprint": alert.fingerprint,
            })
            return False, None
        else:
            # 获取已存在的告警ID
            existing_id = await self.redis.get(dedup_key)
            await self._add_trace_step(trace_id, "dedup_result", "去重检查", "skipped", {
                "description": "发现重复告警",
                "existing_alert_id": existing_id,
                "fingerprint": alert.fingerprint,
            })
            return True, f"相同指纹告警在5分钟内已存在 (alert_id: {existing_id})"

    async def _handle_duplicate(self, alert: Alert, trace_id: str, reason: str):
        """处理重复告警"""
        # 更新原告警的计数
        existing_id = await self.redis.get(f"dedup:{alert.tenant_id}:{alert.fingerprint}")
        if existing_id:
            try:
                existing_alert_id = int(existing_id)
                result = await self.db.execute(
                    select(Alert).where(Alert.id == existing_alert_id)
                )
                existing_alert = result.scalar_one_or_none()
                if existing_alert:
                    existing_alert.fire_count += 1
                    existing_alert.repeat_count += 1
                    await self.db.commit()
            except Exception as e:
                logger.warning("failed_to_update_duplicate", error=str(e))

        await self._finish_trace(trace_id, "duplicate", deduction_reason=reason)

    async def _check_suppress(self, alert: Alert, trace_id: str) -> tuple[bool, Optional[str]]:
        """抑制检查 - 维护期抑制"""
        await self._add_trace_step(trace_id, "suppress_check", "抑制检查", "processing", {})

        now = datetime.utcnow()

        # 查询是否有匹配的维护窗口
        # 简化实现，实际应该查询maintenance_windows表
        # 这里使用Redis缓存的维护窗口配置
        suppress_key = f"suppress:{alert.tenant_id}"
        suppress_config = await self.redis.hgetall(suppress_key)

        if suppress_config:
            # 检查是否匹配维护窗口
            labels = alert.labels or {}
            for key, value in suppress_config.items():
                if key.startswith("window:") and labels.get("cluster") == value:
                    await self._add_trace_step(trace_id, "suppress_result", "抑制检查", "blocked", {
                        "description": "触发维护期抑制",
                        "reason": key,
                    })
                    return True, f"处于维护窗口期"

        await self._add_trace_step(trace_id, "suppress_result", "抑制检查", "passed", {
            "description": "未触发抑制",
        })
        return False, None

    async def _handle_suppressed(self, alert: Alert, trace_id: str, reason: str):
        """处理被抑制的告警"""
        alert.status = "suppressed"
        await self.db.commit()

        await self._finish_trace(trace_id, "suppressed", suppress_reason=reason)

    async def _check_aggregate(self, alert: Alert, trace_id: str) -> Optional[Dict]:
        """聚合检查"""
        await self._add_trace_step(trace_id, "aggregate_check", "聚合检查", "processing", {})

        # 简化实现：检查是否应该聚合
        # 实际应该根据规则配置的聚合窗口和分组条件来判断

        # 尝试获取聚合组
        aggregate_key = f"aggregate:{alert.tenant_id}:{alert.source}:{alert.fingerprint}"
        existing = await self.redis.get(aggregate_key)

        if existing:
            await self._add_trace_step(trace_id, "aggregate_result", "聚合检查", "aggregated", {
                "description": "加入聚合组",
                "existing_alert_id": existing,
            })
            return {
                "aggregated": True,
                "parent_alert_id": existing,
            }

        # 创建新的聚合组
        await self.redis.set(aggregate_key, str(alert.id), ex=300)  # 5分钟聚合窗口

        await self._add_trace_step(trace_id, "aggregate_result", "聚合检查", "new_group", {
            "description": "创建新聚合组",
        })
        return None

    async def _match_rules(self, alert: Alert, trace_id: str) -> tuple[List[AlertRule], List[int]]:
        """规则匹配
        返回: (匹配的规则列表, 通知渠道ID列表)
        """
        await self._add_trace_step(trace_id, "rule_match", "规则匹配", "processing", {})

        # 准备告警数据
        alert_data = {
            "severity": alert.severity,
            "source": alert.source,
            "labels": alert.labels or {},
            "annotations": alert.annotations or {},
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
        }

        # 使用规则引擎匹配
        matched_rules = await self.rule_engine.match_rules(self.db, alert.tenant_id, alert_data)

        matched_rules_info = [
            {"id": r.id, "name": r.name, "priority": r.priority, "actions": r.actions or []}
            for r in matched_rules
        ]

        # 从匹配的规则中提取通知渠道ID
        channel_ids = []
        for rule in matched_rules:
            actions = rule.actions or []
            for action in actions:
                if isinstance(action, int):
                    channel_ids.append(action)
                elif isinstance(action, dict) and action.get("type") == "notify":
                    channel_ids.extend(action.get("channels", []))

        await self._add_trace_step(trace_id, "rule_match", "规则匹配", "success", {
            "description": f"匹配到 {len(matched_rules)} 条规则",
            "matched_rules": matched_rules_info,
            "channel_ids": channel_ids,
        })

        # 更新告警的匹配规则
        alert.matched_rules = matched_rules_info

        return matched_rules, channel_ids

    async def _finalize_alert(
        self,
        alert: Alert,
        matched_rules: List[AlertRule],
        channel_ids: List[int],
        aggregated_info: Optional[Dict],
        trace_id: str
    ):
        """完成告警处理"""
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
        trace_id: str
    ):
        """进入通知队列"""
        if not channel_ids:
            await self._add_trace_step(trace_id, "notification_queued", "通知队列", "skipped", {
                "description": "无匹配通知渠道，跳过通知",
            })
            await self._finish_trace(trace_id, "no_channels")
            return

        # 构建通知消息
        notification_msg = {
            "alert_id": alert.id,
            "trace_id": trace_id,
            "tenant_id": alert.tenant_id,
            "title": alert.title,
            "content": alert.content,
            "severity": alert.severity,
            "channels": channel_ids,
            "labels": alert.labels,
            "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
        }

        # 写入Redis队列 (简化实现，生产应该用PGMQ)
        queue_key = f"queue:notify:{alert.tenant_id}"
        await self.redis.lpush(queue_key, json.dumps(notification_msg))

        await self._add_trace_step(trace_id, "notification_queued", "通知队列", "success", {
            "description": f"已加入通知队列，匹配 {len(matched_rules)} 个渠道",
        })

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
        step = {
            "type": step_type,
            "title": title,
            "status": status,
            "data": data,
            "time": datetime.utcnow().isoformat(),
        }
        await self.redis.rpush(f"{trace_key}:steps", json.dumps(step))
