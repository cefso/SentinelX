"""
SentinelX - 告警分发器
核心处理流程：接入 → 去重 → 抑制 → 聚合 → 规则匹配 → 通知
"""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from apps.alert.models import Alert, AlertTrace, AlertHistory, AlertAggregateGroup, AlertAggregateMember
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

            # 0. 预查找规则（用于去重/抑制/聚合的规则配置）
            dedup_rule = await self._lookup_dedup_rule(alert)
            suppress_rule = await self._lookup_suppress_rule(alert)
            aggregate_rule = await self._lookup_aggregate_rule(alert)

            # 1. 去重检查
            is_duplicate, dedup_reason, dedup_key = await self._check_dedup(alert, trace_id, dedup_rule)
            if is_duplicate:
                await self._handle_duplicate(alert, trace_id, dedup_reason, dedup_key)
                return

            # 2. 抑制检查
            is_suppressed, suppress_reason = await self._check_suppress(alert, trace_id, suppress_rule)
            if is_suppressed:
                await self._handle_suppressed(alert, trace_id, suppress_reason)
                return

            # 3. 聚合检查
            aggregated_info = await self._check_aggregate(alert, trace_id, aggregate_rule)

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

    async def _lookup_dedup_rule(self, alert: Alert) -> Optional[AlertRule]:
        """查找用于去重的规则（取最高优先级规则）"""
        result = await self.db.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == alert.tenant_id,
                AlertRule.is_active == True,
                AlertRule.deduplication_config.isnot(None),
            ).order_by(AlertRule.priority.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _lookup_suppress_rule(self, alert: Alert) -> Optional[AlertRule]:
        """查找用于抑制的规则（取最高优先级规则）"""
        result = await self.db.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == alert.tenant_id,
                AlertRule.is_active == True,
                AlertRule.suppress_config.isnot(None),
            ).order_by(AlertRule.priority.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _lookup_aggregate_rule(self, alert: Alert) -> Optional[AlertRule]:
        """查找用于聚合的规则（取最高优先级规则）"""
        result = await self.db.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == alert.tenant_id,
                AlertRule.is_active == True,
                AlertRule.aggregate_config.isnot(None),
            ).order_by(AlertRule.priority.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def _check_dedup(self, alert: Alert, trace_id: str, rule: Optional[AlertRule] = None) -> tuple[bool, Optional[str]]:
        """去重检查 - 使用Redis实现"""
        dedup_config = getattr(rule, "deduplication_config", None) if rule else None

        # 构建指纹
        if dedup_config and not dedup_config.get("disabled"):
            dims = dedup_config.get("dimensions", {})
            fingerprint_fields = dedup_config.get("fingerprint_fields", ["fingerprint"])

            parts = []
            for field in fingerprint_fields:
                if field == "alert_key":
                    parts.append(str(alert.alert_key or ""))
                elif field == "source":
                    parts.append(str(alert.source or ""))
                elif field == "severity" and dims.get("by_severity"):
                    parts.append(str(alert.severity or ""))
                elif field not in ("alert_key", "source", "severity"):
                    # Fallback to direct field access
                    val = getattr(alert, field, None)
                    parts.append(str(val) if val is not None else "")

            computed_fingerprint = "|".join(parts) if parts else alert.fingerprint
            window_seconds = dedup_config.get("window_seconds", 300)
        else:
            # 兼容：无配置时使用原有逻辑
            computed_fingerprint = alert.fingerprint
            window_seconds = 300

        await self._add_trace_step(trace_id, "dedup_check", "去重检查", "processing", {
            "fingerprint": computed_fingerprint,
            "window_seconds": window_seconds,
        })

        dedup_key = f"dedup:{alert.tenant_id}:{computed_fingerprint}"

        is_new = await self.redis.set(dedup_key, str(alert.id), nx=True, ex=window_seconds)

        if is_new:
            await self._add_trace_step(trace_id, "dedup_result", "去重检查", "passed", {
                "description": "新告警，无重复",
                "fingerprint": computed_fingerprint,
            })
            return False, None, dedup_key
        else:
            existing_id = await self.redis.get(dedup_key)
            await self._add_trace_step(trace_id, "dedup_result", "去重检查", "skipped", {
                "description": "发现重复告警",
                "existing_alert_id": existing_id,
                "fingerprint": computed_fingerprint,
            })
            return True, f"相同指纹告警在{window_seconds}秒内已存在 (alert_id: {existing_id})", dedup_key

    async def _handle_duplicate(self, alert: Alert, trace_id: str, reason: str, dedup_key: Optional[str] = None):
        """处理重复告警"""
        # 更新原告警的计数
        if dedup_key is None:
            dedup_key = f"dedup:{alert.tenant_id}:{alert.fingerprint}"
        existing_id = await self.redis.get(dedup_key)
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

    async def _check_suppress(self, alert: Alert, trace_id: str, rule: Optional[AlertRule] = None) -> tuple[bool, Optional[str]]:
        """抑制检查"""
        suppress_config = getattr(rule, "suppress_config", None) if rule else None

        await self._add_trace_step(trace_id, "suppress_check", "抑制检查", "processing", {
            "config": suppress_config,
        })

        # 基于规则的抑制检查
        if suppress_config and not suppress_config.get("disabled"):
            suppress_type = suppress_config.get("type", "maintenance_window")

            if suppress_type == "maintenance_window":
                # 维护窗口抑制
                maintenance_config = suppress_config.get("maintenance_window", {})
                cluster_labels = maintenance_config.get("cluster_labels", [])
                alert_cluster = (alert.labels or {}).get("cluster", "")

                for cluster_name in cluster_labels:
                    if alert_cluster == cluster_name:
                        await self._add_trace_step(trace_id, "suppress_result", "抑制检查", "blocked", {
                            "description": "触发维护期抑制",
                            "cluster": alert_cluster,
                        })
                        return True, f"处于维护窗口期 (cluster: {alert_cluster})"

            elif suppress_type == "rule_based":
                # 基于规则的抑制：评估条件
                conditions = suppress_config.get("conditions", [])
                condition_mode = suppress_config.get("condition_mode", "and")

                alert_data = self._build_alert_data(alert)
                is_suppressed, reason, _ = self.rule_engine.evaluate_conditions(
                    conditions, condition_mode, alert_data
                )

                if is_suppressed:
                    await self._add_trace_step(trace_id, "suppress_result", "抑制检查", "blocked", {
                        "description": "触发规则抑制",
                        "reason": reason,
                    })
                    return True, f"触发规则抑制: {reason}"
        else:
            # 兼容：无配置时使用原有Redis维护窗口逻辑
            suppress_key = f"suppress:{alert.tenant_id}"
            redis_config = await self.redis.hgetall(suppress_key)

            if redis_config:
                labels = alert.labels or {}
                for key, value in redis_config.items():
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

    async def _check_aggregate(self, alert: Alert, trace_id: str, rule: Optional[AlertRule] = None) -> Optional[Dict]:
        """聚合检查"""
        agg_config = getattr(rule, "aggregate_config", None) if rule else None

        await self._add_trace_step(trace_id, "aggregate_check", "聚合检查", "processing", {
            "config": agg_config,
        })

        if agg_config and not agg_config.get("disabled"):
            # 构建动态 group_key
            group_by_fields = agg_config.get("group_by", ["source", "fingerprint"])
            group_parts = []
            for field in group_by_fields:
                if field == "source":
                    group_parts.append(str(alert.source or ""))
                elif field == "fingerprint":
                    group_parts.append(str(alert.fingerprint or ""))
                elif field == "alert_key":
                    group_parts.append(str(alert.alert_key or ""))
                elif field == "severity":
                    group_parts.append(str(alert.severity or ""))
                elif field == "namespace":
                    group_parts.append(str(alert.namespace or ""))
                elif field.startswith("labels."):
                    label_key = field.split(".", 1)[1]
                    group_parts.append(str((alert.labels or {}).get(label_key, "")))
                else:
                    val = getattr(alert, field, None)
                    group_parts.append(str(val) if val is not None else "")

            group_key = "|".join(group_parts)
            window_seconds = agg_config.get("window_seconds", 300)
            max_count = agg_config.get("max_count", 100)
            store_original = agg_config.get("store_original_alerts", True)

            aggregate_key = f"aggregate:{alert.tenant_id}:{group_key}"
            existing_id = await self.redis.get(aggregate_key)

            if existing_id:
                # 加入现有聚合组
                existing_alert_id = int(existing_id)

                # 检查 max_count 限制
                result = await self.db.execute(
                    select(AlertAggregateGroup).where(
                        AlertAggregateGroup.group_key == aggregate_key,
                        AlertAggregateGroup.tenant_id == alert.tenant_id,
                    )
                )
                group = result.scalar_one_or_none()

                if group is None:
                    # Redis 与 DB 不一致，按新组处理
                    pass
                elif group.alert_count >= max_count:
                    await self._add_trace_step(trace_id, "aggregate_result", "聚合检查", "max_exceeded", {
                        "description": "聚合组已达上限，跳过聚合",
                        "group_key": group_key,
                        "max_count": max_count,
                    })
                    return None
                else:
                    # 创建聚合组成员记录
                    if store_original:
                        member = AlertAggregateMember(
                            tenant_id=alert.tenant_id,
                            group_id=group.id,
                            alert_id=alert.id,
                        )
                        self.db.add(member)

                    # 更新聚合组计数
                    group.alert_count += 1
                    group.last_alert_at = datetime.utcnow()
                    group.latest_alert_id = alert.id
                    await self.db.commit()

                    await self._add_trace_step(trace_id, "aggregate_result", "聚合检查", "aggregated", {
                        "description": "加入聚合组",
                        "existing_alert_id": existing_id,
                        "group_key": group_key,
                    })
                    return {
                        "aggregated": True,
                        "parent_alert_id": existing_id,
                        "group_key": group_key,
                    }

            # 创建新聚合组
            new_group = AlertAggregateGroup(
                tenant_id=alert.tenant_id,
                group_key=aggregate_key,
                rule_id=rule.id if rule else None,
                alert_count=1,
                fired_at=alert.fired_at,
                last_alert_at=alert.fired_at,
                first_alert_id=alert.id,
                latest_alert_id=alert.id,
            )
            self.db.add(new_group)
            await self.db.flush()  # 获取 group.id

            if store_original:
                member = AlertAggregateMember(
                    tenant_id=alert.tenant_id,
                    group_id=new_group.id,
                    alert_id=alert.id,
                )
                self.db.add(member)

            await self.db.commit()

            # 设置 Redis TTL
            await self.redis.set(aggregate_key, str(alert.id), ex=window_seconds)

            await self._add_trace_step(trace_id, "aggregate_result", "聚合检查", "new_group", {
                "description": "创建新聚合组",
                "group_key": group_key,
            })
            return None
        else:
            # 兼容：无配置时使用原有逻辑
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

            await self.redis.set(aggregate_key, str(alert.id), ex=300)

            await self._add_trace_step(trace_id, "aggregate_result", "聚合检查", "new_group", {
                "description": "创建新聚合组",
            })
            return None

    def _build_alert_data(self, alert: Alert) -> Dict[str, Any]:
        """构建告警数据字典，用于规则条件评估"""
        return {
            # 基础字段
            "alert_key": alert.alert_key,
            "title": alert.title,
            "content": alert.content,
            "severity": alert.severity,
            "status": alert.status,
            "source": alert.source,
            # 云产品字段
            "namespace": alert.namespace,
            "instance_id": alert.instance_id,
            "instance_name": alert.instance_name,
            # 指标字段
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
            # 标签/注解/原始数据
            "labels": alert.labels or {},
            "annotations": alert.annotations or {},
            "raw_data": alert.raw_data or {},
            # 统计字段
            "fire_count": alert.fire_count,
            "repeat_count": alert.repeat_count,
            "escalation_count": alert.escalation_count,
            # 时间字段
            "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
            # 追踪字段
            "trace_id": alert.trace_id,
        }

    async def _match_rules(self, alert: Alert, trace_id: str) -> tuple[List[AlertRule], List[int]]:
        """规则匹配
        返回: (匹配的规则列表, 通知渠道ID列表)
        """
        await self._add_trace_step(trace_id, "rule_match", "规则匹配", "processing", {})

        alert_data = self._build_alert_data(alert)

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
