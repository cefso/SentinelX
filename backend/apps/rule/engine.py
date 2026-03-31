"""
SentinelX - 规则引擎
基于条件的告警路由匹配
"""
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.rule.models import AlertRule

import structlog

logger = structlog.get_logger()


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

    async def match(self, tenant_id: str, alert_data: Dict[str, Any]) -> List[AlertRule]:
        """
        匹配告警到规则
        返回所有匹配的规则，按优先级排序
        """
        # 查询启用的规则
        result = await select(AlertRule).where(
            AlertRule.tenant_id == tenant_id,
            AlertRule.is_active == True
        ).order_by(AlertRule.priority.desc())

        # 这里需要session，但engine可能没有session
        # 简化实现，实际使用需要传入session
        return []

    async def match_rules(self, db: AsyncSession, tenant_id: str, alert_data: Dict[str, Any]) -> List[AlertRule]:
        """匹配规则（带数据库会话）"""
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.tenant_id == tenant_id,
                AlertRule.is_active == True
            ).order_by(AlertRule.priority.desc())
        )
        rules = result.scalars().all()

        matched = []
        for rule in rules:
            conditions = rule.conditions or []
            condition_mode = rule.condition_mode or "and"

            is_match, reason = self.evaluate_conditions(
                conditions,
                condition_mode,
                alert_data
            )

            if is_match:
                # 更新规则统计
                rule.match_count += 1
                matched.append(rule)
                logger.info("rule_matched", rule_id=rule.id, rule_name=rule.name)

        await db.commit()
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
