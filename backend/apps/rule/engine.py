"""
SentinelX - 规则引擎
基于条件的告警路由匹配
"""
import hashlib
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from apps.rule.models import AlertRule
from apps.rule.suppress_timing import is_suppress_rule_in_effect
from apps.alert.models import Alert, AlertAggregateGroup, AlertAggregateMember
from apps.alert.services.alert_utils import alert_to_dict

import structlog

logger = structlog.get_logger()

# 策略规则 code 前缀（不参与路由「规则匹配」统计）
_STRATEGY_CODE_PREFIXES = ("_dedup_%", "_suppress_%", "_aggregate_%")


def _stable_hash(value: str) -> str:
    """跨进程稳定的短哈希，用于 Redis 去重/聚合键。"""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


_NUMERIC_ID_FIELDS = frozenset({"source_id", "assignee"})
_INTEGER_FIELDS = frozenset({"fire_count", "repeat_count", "escalation_count"})


def _coerce_int(value: Any) -> Any:
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _is_effective_dedup_config(config: Any) -> bool:
    """有效去重配置：排除 JSON null、空对象及未启用规则。"""
    if not config or not isinstance(config, dict):
        return False
    if config.get("disabled", not config.get("enabled", False)):
        return False
    return True


@dataclass
class AlertProcessResult:
    """告警处理结果"""
    is_duplicate: bool = False
    duplicate_of_alert_id: Optional[str] = None
    is_suppressed: bool = False
    suppress_reason: Optional[str] = None
    aggregated_info: Optional[Dict[str, Any]] = None
    matched_rules: List[AlertRule] = field(default_factory=list)
    channel_ids: List[int] = field(default_factory=list)
    template_map: Dict[int, int | None] = field(default_factory=dict)  # channel_id -> template_id
    trace_steps: List[Dict] = field(default_factory=list)


class RuleEngine:
    """
    规则引擎 - 评估告警是否匹配规则
    """

    OPERATORS = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "gt": lambda a, b: float(a) > float(b) if a is not None else False,
        "gte": lambda a, b: float(a) >= float(b) if a is not None else False,
        "lt": lambda a, b: float(a) < float(b) if a is not None else False,
        "lte": lambda a, b: float(a) <= float(b) if a is not None else False,
        "contains": lambda a, b: b in str(a) if a is not None else False,
        "not_contains": lambda a, b: b not in str(a) if a is not None else True,
        "regex": lambda a, b: bool(re.match(b, str(a))) if a is not None else False,
        "in": lambda a, b: a in b if isinstance(b, list) else a == b,
        "not_in": lambda a, b: a not in b if isinstance(b, list) else a != b,
        "exists": lambda a, b: a is not None if b else a is None,
        "is_empty": lambda a, b: (a is None or a == "" or a == {}) if b else False,
    }

    def __init__(self):
        pass

    def _normalize_condition_value(self, field: str, operator: str, value: Any) -> Any:
        """页面条件值规范化（如 source_id 的 in 列表存为字符串）。"""
        if operator in ("in", "not_in") and isinstance(value, list):
            if field in _NUMERIC_ID_FIELDS | _INTEGER_FIELDS:
                return [_coerce_int(v) for v in value]
            return value

        if field in _NUMERIC_ID_FIELDS | _INTEGER_FIELDS:
            return _coerce_int(value)
        return value

    async def _record_strategy_rule_match(self, db: AsyncSession, rule: AlertRule) -> None:
        """策略规则命中统计（去重/抑制/聚合等）。"""
        if db is None:
            return
        try:
            # alert_rules.last_match_at 为 naive UTC，与模型列类型一致
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            rule.match_count = (getattr(rule, "match_count", None) or 0) + 1
            rule.last_match_at = now
            await db.commit()
        except Exception as e:
            logger.warning(
                "strategy_rule_match_count_failed",
                rule_id=getattr(rule, "id", None),
                error=str(e),
            )
            await db.rollback()

    async def match_rules(self, db: AsyncSession, tenant_id: str, alert_data: Dict[str, Any]) -> List[AlertRule]:
        """匹配规则（带数据库会话）"""
        query = select(AlertRule).where(
            AlertRule.tenant_id == tenant_id,
            AlertRule.is_active == True,
        )
        for prefix in _STRATEGY_CODE_PREFIXES:
            query = query.where(~AlertRule.code.like(prefix))
        result = await db.execute(query.order_by(AlertRule.priority.desc()))
        rules = result.scalars().all()

        logger.debug("rules_evaluating", tenant_id=tenant_id, total_rules=len(rules))

        matched = []
        for rule in rules:
            conditions = rule.conditions or []
            condition_mode = rule.condition_mode or "and"

            is_match, reason, eval_details = self.evaluate_conditions(
                conditions,
                condition_mode,
                alert_data
            )

            if is_match:
                # 更新规则统计
                rule.match_count += 1
                matched.append(rule)
                logger.info("rule_matched", rule_id=rule.id, rule_name=rule.name)
            else:
                logger.debug("rule_not_matched", rule_id=rule.id, rule_name=rule.name, reason=reason)

        await db.commit()
        logger.debug("rules_evaluation_complete", tenant_id=tenant_id, matched_count=len(matched))
        return matched

    def evaluate_conditions(
        self,
        conditions: List[Dict[str, Any]],
        condition_mode: str,
        alert_data: Dict[str, Any]
    ) -> tuple[bool, Optional[str], List[Dict[str, Any]]]:
        """
        评估条件
        返回: (是否匹配, 原因, 评估详情)
        """
        if not conditions:
            return True, "No conditions", []

        results = []
        for condition in conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "eq")
            expected_value = condition.get("value")

            # 获取字段值
            actual_value = self._get_field_value(alert_data, field)
            expected_value = self._normalize_condition_value(field, operator, expected_value)

            # 执行比较
            evaluator = self.OPERATORS.get(operator)
            if not evaluator:
                results.append({
                    "field": field,
                    "operator": operator,
                    "expected": expected_value,
                    "actual": actual_value,
                    "matched": False,
                    "error": f"Unknown operator: {operator}",
                })
                continue

            try:
                matched = evaluator(actual_value, expected_value)
                results.append({
                    "field": field,
                    "operator": operator,
                    "expected": expected_value,
                    "actual": actual_value,
                    "matched": matched,
                })
            except Exception as e:
                results.append({
                    "field": field,
                    "operator": operator,
                    "expected": expected_value,
                    "actual": actual_value,
                    "matched": False,
                    "error": str(e),
                })

        # 计算最终结果
        if condition_mode == "and":
            all_matched = all(r.get("matched", False) for r in results)
        else:  # or
            all_matched = any(r.get("matched", False) for r in results)

        reason = None
        if not all_matched:
            failed_fields = [r["field"] for r in results if not r.get("matched")]
            reason = f"Conditions not met for fields: {failed_fields}"

        return all_matched, reason, results

    def _get_field_value(self, data: Dict[str, Any], field: str) -> Any:
        """
        获取嵌套字段值
        支持: severity, labels.cluster, annotations.description
        """
        parts = field.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    async def process_alert(
        self,
        db: AsyncSession,
        redis: Redis,
        alert: Alert,
        trace_id: str,
        add_trace_step: Callable = None
    ) -> AlertProcessResult:
        """
        统一处理告警：去重、抑制、聚合、规则匹配
        """
        logger.debug("process_alert_start", alert_id=alert.id, trace_id=trace_id, tenant_id=alert.tenant_id)
        result = AlertProcessResult()

        # 1. 去重检查
        is_duplicate, dedup_result, duplicate_of_alert_id = await self._check_dedup(
            db, redis, alert, trace_id, add_trace_step
        )
        if is_duplicate:
            result.is_duplicate = True
            result.duplicate_of_alert_id = duplicate_of_alert_id
            result.trace_steps = dedup_result
            return result

        # 2. 抑制检查
        is_suppressed, reason, suppress_result = await self._check_suppress(db, redis, alert, trace_id, add_trace_step)
        if is_suppressed:
            result.is_suppressed = True
            result.suppress_reason = reason
            result.trace_steps = suppress_result
            return result

        # 3. 聚合检查
        aggregated_info, agg_result = await self._check_aggregate(db, redis, alert, trace_id, add_trace_step)
        result.aggregated_info = aggregated_info

        # 4. 规则匹配（获取通知渠道）
        matched_rules, channel_ids, template_map, match_result = await self._match_rules(db, alert, trace_id, add_trace_step)
        result.matched_rules = matched_rules
        result.channel_ids = channel_ids
        result.template_map = template_map

        # 合并所有 trace_steps
        result.trace_steps = dedup_result + suppress_result + agg_result + match_result

        return result

    async def _check_dedup(
        self,
        db: AsyncSession,
        redis: Redis,
        alert: Alert,
        trace_id: str,
        add_trace_step: Callable = None
    ) -> tuple[bool, List[Dict], Optional[str]]:
        """去重检查 — 支持多规则"""
        trace_steps = []

        async def _add_step(step_type, title, status, data):
            step = {
                "type": step_type,
                "title": title,
                "status": status,
                "data": data,
                "time": datetime.now(timezone.utc).isoformat(),
            }
            trace_steps.append(step)
            if add_trace_step:
                await add_trace_step(trace_id, step_type, title, status, data)

        await _add_step("dedup_check", "去重检查", "processing", {"description": "检查是否为重复告警"})

        # 查找所有匹配的去重规则（仅含有效去重配置）
        dedup_rules = await self._find_matching_dedup_rules(db, alert)
        active_dedup_rules = [
            r for r in dedup_rules
            if _is_effective_dedup_config(getattr(r, "deduplication_config", None))
        ]
        matched_rule_names = [{"id": r.id, "name": r.name} for r in active_dedup_rules]

        if not active_dedup_rules:
            await _add_step("dedup_result", "去重检查", "passed", {"description": "未配置去重规则，跳过"})
            return False, trace_steps, None

        # 遍历所有匹配的去重规则，任一 Redis 命中即去重
        for dedup_rule in active_dedup_rules:
            dedup_config = dedup_rule.deduplication_config
            dedup_type = dedup_config.get("dedup_type", "fingerprint")
            window_seconds = dedup_config.get("window_seconds", 300)

            if dedup_type == "fingerprint":
                fp_fields = dedup_config.get("fingerprint_fields", ["alert_key"])
                dedup_key_parts = [str(alert.tenant_id)]

                for field_name in fp_fields:
                    if field_name == "alert_key":
                        dedup_key_parts.append(str(alert.alert_key or ""))
                    elif field_name == "fingerprint":
                        dedup_key_parts.append(str(alert.fingerprint or ""))
                    elif field_name == "source":
                        dedup_key_parts.append(str(alert.source or ""))
                    elif field_name == "severity":
                        dedup_key_parts.append(str(alert.severity or ""))
                    elif field_name.startswith("labels."):
                        label_key = field_name.split(".", 1)[1]
                        dedup_key_parts.append(str((alert.labels or {}).get(label_key, "")))
                    else:
                        val = getattr(alert, field_name, None)
                        dedup_key_parts.append(str(val) if val is not None else "")

                dedup_key = "dedup:" + ":".join(dedup_key_parts)

            elif dedup_type == "condition":
                conditions = dedup_config.get("conditions", [])
                condition_mode = dedup_config.get("condition_mode", "and")

                if not conditions:
                    continue

                alert_data = self._alert_to_dict(alert)
                is_match, _, _ = self.evaluate_conditions(conditions, condition_mode, alert_data)

                if not is_match:
                    continue

                cond_sig = "|".join(
                    f"{c.get('field')}:{c.get('operator')}:{c.get('value')}"
                    for c in conditions
                )
                dedup_key = f"dedup:cond:{_stable_hash(cond_sig)}:{alert.tenant_id}"
            else:
                continue

            existing = await redis.get(dedup_key)
            if existing:
                existing_id = existing.decode("utf-8") if isinstance(existing, bytes) else str(existing)
                # MQ 重投同一告警时，Redis 键可能指向自身，不应误判为重复
                if existing_id == str(alert.id):
                    continue

                logger.info(
                    "dedup_blocked",
                    alert_id=alert.id,
                    trace_id=trace_id,
                    dedup_key=dedup_key,
                    rule_name=dedup_rule.name,
                    duplicate_of=existing_id,
                )
                await _add_step("dedup_result", "去重检查", "blocked", {
                    "description": f"触发去重，已存在告警: {existing_id}",
                    "details": {
                        "matched_rules": matched_rule_names,
                        "blocked_by_rule": dedup_rule.name,
                        "duplicate_of_alert_id": existing_id,
                    },
                })
                await self._record_strategy_rule_match(db, dedup_rule)
                return True, trace_steps, existing_id

            await redis.set(dedup_key, str(alert.id), ex=window_seconds)
            await self._record_strategy_rule_match(db, dedup_rule)

        await _add_step("dedup_result", "去重检查", "passed", {
            "description": "未触发去重",
            "details": {"matched_rules": matched_rule_names} if matched_rule_names else None,
        })
        return False, trace_steps, None

    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """将告警转换为字典"""
        return alert_to_dict(alert)

    async def _find_matching_dedup_rules(self, db: AsyncSession, alert: Alert) -> List[AlertRule]:
        """查找所有匹配的去重规则（按优先级排序，条件匹配）"""
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == alert.tenant_id,
                AlertRule.is_active == True,
                AlertRule.deduplication_config.isnot(None),
            ).order_by(AlertRule.priority.desc())
        )
        rules = [
            r for r in result.scalars().all()
            if _is_effective_dedup_config(r.deduplication_config)
        ]
        alert_data = self._alert_to_dict(alert)
        matched = []
        for rule in rules:
            conditions = rule.conditions or []
            if not conditions:
                matched.append(rule)
                continue
            ok, _, _ = self.evaluate_conditions(conditions, rule.condition_mode or "and", alert_data)
            if ok:
                matched.append(rule)
        return matched

    def _get_suppress_rule_conditions(self, rule: AlertRule) -> tuple[List[Dict[str, Any]], str]:
        """获取抑制规则的生效条件（优先 rule.conditions，兼容旧 rule_based 配置）"""
        conditions = rule.conditions or []
        condition_mode = rule.condition_mode or "and"
        if conditions:
            return conditions, condition_mode
        suppress_config = getattr(rule, "suppress_config", None) or {}
        rb = suppress_config.get("rule_based") or {}
        legacy = rb.get("conditions") or suppress_config.get("conditions", [])
        return legacy, rb.get("condition_mode", suppress_config.get("condition_mode", "and"))

    async def _find_matching_suppress_rules(self, db: AsyncSession, alert: Alert) -> List[AlertRule]:
        """查找所有匹配的抑制规则（按优先级排序，条件匹配）"""
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == alert.tenant_id,
                AlertRule.is_active == True,
                AlertRule.suppress_config.isnot(None),
            ).order_by(AlertRule.priority.desc())
        )
        rules = result.scalars().all()
        alert_data = self._alert_to_dict(alert)
        matched = []
        for rule in rules:
            conditions, condition_mode = self._get_suppress_rule_conditions(rule)
            if not conditions:
                matched.append(rule)
                continue
            ok, _, _ = self.evaluate_conditions(conditions, condition_mode, alert_data)
            if ok:
                matched.append(rule)
        return matched

    async def _find_matching_aggregate_rules(self, db: AsyncSession, alert: Alert) -> List[AlertRule]:
        """查找所有匹配的聚合规则（按优先级排序，条件匹配）"""
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == alert.tenant_id,
                AlertRule.is_active == True,
                AlertRule.aggregate_config.isnot(None),
            ).order_by(AlertRule.priority.desc())
        )
        rules = result.scalars().all()
        alert_data = self._alert_to_dict(alert)
        matched = []
        for rule in rules:
            conditions = rule.conditions or []
            if not conditions:
                matched.append(rule)
                continue
            ok, _, _ = self.evaluate_conditions(conditions, rule.condition_mode or "and", alert_data)
            if ok:
                matched.append(rule)
        return matched

    async def _check_suppress(
        self,
        db: AsyncSession,
        redis: Redis,
        alert: Alert,
        trace_id: str,
        add_trace_step: Callable = None
    ) -> tuple[bool, Optional[str], List[Dict]]:
        """抑制检查 — 支持多规则"""
        trace_steps = []

        async def _add_step(step_type, title, status, data):
            step = {
                "type": step_type,
                "title": title,
                "status": status,
                "data": data,
                "time": datetime.now(timezone.utc).isoformat(),
            }
            trace_steps.append(step)
            if add_trace_step:
                await add_trace_step(trace_id, step_type, title, status, data)

        await _add_step("suppress_check", "抑制检查", "processing", {"description": "检查是否应该抑制此告警"})

        # 查找所有匹配的抑制规则
        suppress_rules = await self._find_matching_suppress_rules(db, alert)
        matched_rule_names = [{"id": r.id, "name": r.name} for r in suppress_rules]

        if not suppress_rules:
            # 无规则配置，检查 Redis 维护窗口（旧逻辑兼容）
            suppress_key = f"suppress:{alert.tenant_id}"
            redis_config = await redis.hgetall(suppress_key)

            if redis_config:
                labels = alert.labels or {}
                for key, value in redis_config.items():
                    if key.startswith("window:") and labels.get("cluster") == value:
                        logger.info("suppress_triggered", alert_id=alert.id, trace_id=trace_id, reason="redis_maintenance_window")
                        await _add_step("suppress_result", "抑制检查", "blocked", {
                            "description": "处于维护窗口期"
                        })
                        return True, "处于维护窗口期", trace_steps

            await _add_step("suppress_result", "抑制检查", "passed", {"description": "未配置抑制规则，跳过"})
            return False, None, trace_steps

        now = datetime.now(timezone.utc)
        # 遍历所有匹配的抑制规则，任一在生效窗口内即抑制
        for suppress_rule in suppress_rules:
            suppress_config = getattr(suppress_rule, "suppress_config", None)
            if not suppress_config:
                continue

            if suppress_config.get("disabled", not suppress_config.get("enabled", False)):
                continue

            in_effect, window_reason = is_suppress_rule_in_effect(
                suppress_config,
                now,
                rule_created_at=getattr(suppress_rule, "created_at", None),
            )
            if not in_effect:
                continue

            logger.info(
                "suppress_triggered",
                alert_id=alert.id,
                trace_id=trace_id,
                rule_name=suppress_rule.name,
                window_reason=window_reason,
            )
            await self._record_strategy_rule_match(db, suppress_rule)

            await _add_step("suppress_result", "抑制检查", "blocked", {
                "description": f"触发规则抑制: {suppress_rule.name}",
                "details": {
                    "matched_rules": matched_rule_names,
                    "triggered_by_rule": suppress_rule.name,
                    "duration_minutes": suppress_config.get("duration_minutes"),
                    "effective_until": suppress_config.get("effective_until"),
                    "in_effect": True,
                    "window_reason": window_reason,
                },
            })
            return True, f"触发规则抑制: {suppress_rule.name}", trace_steps

        logger.info("suppress_check_passed", alert_id=alert.id, trace_id=trace_id)
        await _add_step("suppress_result", "抑制检查", "passed", {
            "description": "未触发抑制（无生效窗口内的匹配规则）",
            "details": {"matched_rules": matched_rule_names} if matched_rule_names else None,
        })
        return False, None, trace_steps

    async def _check_aggregate(
        self,
        db: AsyncSession,
        redis: Redis,
        alert: Alert,
        trace_id: str,
        add_trace_step: Callable = None
    ) -> tuple[Optional[Dict], List[Dict]]:
        """聚合检查 — 支持多规则，使用第一个匹配的（按优先级）"""
        trace_steps = []

        async def _add_step(step_type, title, status, data):
            step = {
                "type": step_type,
                "title": title,
                "status": status,
                "data": data,
                "time": datetime.now(timezone.utc).isoformat(),
            }
            trace_steps.append(step)
            if add_trace_step:
                await add_trace_step(trace_id, step_type, title, status, data)

        await _add_step("aggregate_check", "聚合检查", "processing", {"description": "检查是否需要聚合此告警"})

        # 查找所有匹配的聚合规则，使用第一个（最高优先级）
        aggregate_rules = await self._find_matching_aggregate_rules(db, alert)
        matched_rule_names = [{"id": r.id, "name": r.name} for r in aggregate_rules]

        if not aggregate_rules:
            await _add_step("aggregate_result", "聚合检查", "skipped", {"description": "未配置聚合规则，跳过"})
            return None, trace_steps

        aggregate_rule = aggregate_rules[0]
        agg_config = getattr(aggregate_rule, "aggregate_config", None)

        if agg_config and not agg_config.get("disabled", not agg_config.get("enabled", False)):
            agg_mode = agg_config.get("mode", "group_by")
            window_seconds = agg_config.get("window_seconds", 300)
            max_count = agg_config.get("max_count", 100)
            store_original = agg_config.get("store_original_alerts", True)

            if agg_mode == "condition":
                # 条件模式：评估条件决定聚合组
                conditions = agg_config.get("conditions", [])
                condition_mode = agg_config.get("condition_mode", "and")

                alert_data = self._alert_to_dict(alert)
                is_match, reason, _ = self.evaluate_conditions(
                    conditions, condition_mode, alert_data
                )

                if is_match and conditions:
                    cond_sig = "|".join(
                        f"{c.get('field')}:{c.get('operator')}:{c.get('value')}"
                        for c in conditions
                    )
                    group_key = f"cond:{hash(cond_sig)}"
                elif is_match:
                    group_key = "cond:match"
                else:
                    # 条件不匹配，跳过聚合
                    await _add_step("aggregate_result", "聚合检查", "skipped", {
                        "description": "聚合条件不匹配",
                        "details": {
                            "matched_rules": matched_rule_names,
                            "rule_name": aggregate_rule.name,
                        },
                    })
                    return None, trace_steps
            else:
                # group_by 模式（默认）：按字段值聚合
                group_by_fields = agg_config.get("group_by", ["source", "fingerprint"])
                group_parts = []
                for field_name in group_by_fields:
                    if field_name == "source":
                        group_parts.append(str(alert.source or ""))
                    elif field_name == "fingerprint":
                        group_parts.append(str(alert.fingerprint or ""))
                    elif field_name == "alert_key":
                        group_parts.append(str(alert.alert_key or ""))
                    elif field_name == "severity":
                        group_parts.append(str(alert.severity or ""))
                    elif field_name == "namespace":
                        group_parts.append(str(alert.namespace or ""))
                    elif field_name.startswith("labels."):
                        label_key = field_name.split(".", 1)[1]
                        group_parts.append(str((alert.labels or {}).get(label_key, "")))
                    else:
                        val = getattr(alert, field_name, None)
                        if val is None and "." in field_name:
                            group_parts.append(str((alert.labels or {}).get(field_name.split(".", 1)[1], "")))
                        else:
                            group_parts.append(str(val) if val is not None else "")

                group_key = "|".join(group_parts)

            aggregate_key = f"aggregate:{alert.tenant_id}:{group_key}"
            existing_id = await redis.get(aggregate_key)

            if existing_id:
                # 加入现有聚合组
                existing_alert_id = int(existing_id)

                # 检查 max_count 限制
                result = await db.execute(
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
                    await _add_step("aggregate_result", "聚合检查", "skipped", {
                        "description": f"聚合组达到上限 ({max_count})",
                        "details": {
                            "matched_rules": matched_rule_names,
                            "rule_name": aggregate_rule.name,
                            "group_key": group_key,
                        },
                    })
                    return None, trace_steps
                else:
                    # 创建聚合组成员记录
                    if store_original:
                        member = AlertAggregateMember(
                            tenant_id=alert.tenant_id,
                            group_id=group.id,
                            alert_id=alert.id,
                        )
                        db.add(member)

                    # 更新聚合组计数
                    group.alert_count += 1
                    group.last_alert_at = datetime.now(timezone.utc)
                    await db.commit()

                    logger.info("aggregate_joined", alert_id=alert.id, trace_id=trace_id, group_key=group_key, parent_id=existing_id)
                    await _add_step("aggregate_result", "聚合检查", "aggregated", {
                        "description": f"加入聚合组，现有告警数: {group.alert_count}",
                        "details": {
                            "matched_rules": matched_rule_names,
                            "rule_name": aggregate_rule.name,
                            "group_key": group_key,
                            "parent_alert_id": existing_id,
                        },
                    })
                    return {
                        "aggregated": True,
                        "parent_alert_id": existing_id,
                        "group_key": group_key,
                    }, trace_steps

            # 创建新聚合组
            new_group = AlertAggregateGroup(
                tenant_id=alert.tenant_id,
                group_key=aggregate_key,
                rule_id=aggregate_rule.id if aggregate_rule else None,
                alert_count=1,
                fired_at=alert.fired_at,
                last_alert_at=alert.fired_at,
            )
            db.add(new_group)
            await db.flush()

            if store_original:
                member = AlertAggregateMember(
                    tenant_id=alert.tenant_id,
                    group_id=new_group.id,
                    alert_id=alert.id,
                )
                db.add(member)

            await db.commit()

            # 设置 Redis TTL
            await redis.set(aggregate_key, str(alert.id), ex=window_seconds)

            logger.info("aggregate_new_group", alert_id=alert.id, trace_id=trace_id, group_key=group_key)
            await _add_step("aggregate_result", "聚合检查", "new_group", {
                "description": "创建新聚合组",
                "details": {
                    "matched_rules": matched_rule_names,
                    "rule_name": aggregate_rule.name,
                    "group_key": group_key,
                },
            })
            return None, trace_steps
        else:
            # 没有聚合配置，跳过聚合
            await _add_step("aggregate_result", "聚合检查", "skipped", {"description": "未配置聚合规则，跳过"})
            return None, trace_steps

    async def _match_rules(
        self,
        db: AsyncSession,
        alert: Alert,
        trace_id: str,
        add_trace_step: Callable = None
    ) -> tuple[List[AlertRule], List[int], Dict[int, int | None], List[Dict]]:
        """规则匹配
        返回: (匹配的规则列表, 通知渠道ID列表, {channel_id: template_id}, trace步骤)
        """
        trace_steps = []

        async def _add_step(step_type, title, status, data):
            step = {
                "type": step_type,
                "title": title,
                "status": status,
                "data": data,
                "time": datetime.now(timezone.utc).isoformat(),
            }
            trace_steps.append(step)
            if add_trace_step:
                await add_trace_step(trace_id, step_type, title, status, data)

        await _add_step("rule_match", "规则匹配", "processing", {"description": "匹配告警规则"})

        alert_data = self._alert_to_dict(alert)

        # 使用规则引擎匹配
        matched_rules = await self.match_rules(db, alert.tenant_id, alert_data)

        # 从匹配的规则中提取通知渠道ID 和 template_map
        channel_ids = []
        template_map: Dict[int, int | None] = {}
        for rule in matched_rules:
            actions = rule.actions or []
            for action in actions:
                if isinstance(action, int):
                    channel_ids.append(action)
                elif isinstance(action, dict):
                    if action.get("type") == "notify":
                        channel_ids.extend(action.get("channels", []))
                    elif action.get("channel_id"):
                        # 新格式: {"channel_id": 1, "template_id": 5}
                        channel_ids.append(action.get("channel_id"))

        logger.info("rule_matched", alert_id=alert.id, trace_id=trace_id, matched_count=len(matched_rules), channel_ids=channel_ids)

        matched_rules_info = [{"id": r.id, "name": r.name, "priority": r.priority} for r in matched_rules]
        await _add_step("rule_match_result", "规则匹配", "success", {
            "description": f"匹配到 {len(matched_rules)} 条规则",
            "matched_rules": matched_rules_info,
            "channel_ids": channel_ids,
            "template_map": template_map,
        })

        return matched_rules, channel_ids, template_map, trace_steps
