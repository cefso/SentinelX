"""
SentinelX - 规则引擎测试
"""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from apps.rule.engine import RuleEngine
from apps.rule.suppress_timing import (
    compute_suppress_effective_until,
    enrich_suppress_config,
    is_suppress_rule_in_effect,
)
from apps.alert.models import Alert


def test_rule_engine_operators():
    """测试规则引擎操作符"""
    engine = RuleEngine()

    # eq
    assert engine.OPERATORS["eq"]("a", "a") is True
    assert engine.OPERATORS["eq"]("a", "b") is False

    # ne
    assert engine.OPERATORS["ne"]("a", "b") is True
    assert engine.OPERATORS["ne"]("a", "a") is False

    # gt
    assert engine.OPERATORS["gt"](10, 5) is True
    assert engine.OPERATORS["gt"](5, 10) is False

    # gte
    assert engine.OPERATORS["gte"](10, 10) is True
    assert engine.OPERATORS["gte"](5, 10) is False

    # lt
    assert engine.OPERATORS["lt"](5, 10) is True
    assert engine.OPERATORS["lt"](10, 5) is False

    # lte
    assert engine.OPERATORS["lte"](10, 10) is True
    assert engine.OPERATORS["lte"](10, 5) is False

    # contains
    assert engine.OPERATORS["contains"]("hello world", "world") is True
    assert engine.OPERATORS["contains"]("hello", "world") is False

    # regex
    assert engine.OPERATORS["regex"]("test123", r"test\d+") is True
    assert engine.OPERATORS["regex"]("test", r"test\d+") is False

    # in
    assert engine.OPERATORS["in"]("a", ["a", "b", "c"]) is True
    assert engine.OPERATORS["in"]("d", ["a", "b", "c"]) is False

    # not_in
    assert engine.OPERATORS["not_in"]("d", ["a", "b", "c"]) is True
    assert engine.OPERATORS["not_in"]("a", ["a", "b", "c"]) is False


def test_get_field_value():
    """测试获取嵌套字段值"""
    engine = RuleEngine()

    data = {
        "severity": "critical",
        "labels": {
            "cluster": "prod",
            "env": "production"
        }
    }

    assert engine._get_field_value(data, "severity") == "critical"
    assert engine._get_field_value(data, "labels.cluster") == "prod"
    assert engine._get_field_value(data, "labels.env") == "production"
    assert engine._get_field_value(data, "nonexistent") is None
    assert engine._get_field_value(data, "labels.nonexistent") is None


def test_evaluate_conditions_and_mode():
    """测试AND条件模式"""
    engine = RuleEngine()

    conditions = [
        {"field": "severity", "operator": "eq", "value": "critical"},
        {"field": "source", "operator": "eq", "value": "prometheus"},
    ]

    alert_data = {
        "severity": "critical",
        "source": "prometheus",
    }

    matched, reason, results = engine.evaluate_conditions(conditions, "and", alert_data)
    assert matched is True

    # 一个条件不满足
    alert_data["severity"] = "high"
    matched, reason, results = engine.evaluate_conditions(conditions, "and", alert_data)
    assert matched is False


def test_evaluate_conditions_or_mode():
    """测试OR条件模式"""
    engine = RuleEngine()

    conditions = [
        {"field": "severity", "operator": "eq", "value": "critical"},
        {"field": "source", "operator": "eq", "value": "prometheus"},
    ]

    # 只有一个条件满足
    alert_data = {
        "severity": "critical",
        "source": "zabbix",
    }

    matched, reason, results = engine.evaluate_conditions(conditions, "or", alert_data)
    assert matched is True


def test_evaluate_conditions_regex():
    """测试正则匹配"""
    engine = RuleEngine()

    conditions = [
        {"field": "alert_key", "operator": "regex", "value": r"host:.*:cpu"},
    ]

    alert_data = {"alert_key": "host:192.168.1.1:cpu_high"}
    matched, reason, results = engine.evaluate_conditions(conditions, "and", alert_data)
    assert matched is True


def test_evaluate_conditions_in():
    """测试IN操作符"""
    engine = RuleEngine()

    conditions = [
        {"field": "severity", "operator": "in", "value": ["critical", "high"]},
    ]

    alert_data = {"severity": "critical"}
    matched, _, _ = engine.evaluate_conditions(conditions, "and", alert_data)
    assert matched is True

    alert_data = {"severity": "medium"}
    matched, _, _ = engine.evaluate_conditions(conditions, "and", alert_data)
    assert matched is False


def test_field_values_schema():
    """测试 FieldValuesResponse Schema 序列化"""
    from apps.rule.schemas import FieldValuesResponse, FieldValueItem

    resp = FieldValuesResponse(
        field="namespace",
        values=[
            FieldValueItem(value="acs_ecs_dashboard", count=156),
            FieldValueItem(value="acs_rds_dashboard", count=42),
        ],
        total=2,
        limit=20,
        offset=0,
    )
    data = resp.model_dump()

    assert data["field"] == "namespace"
    assert len(data["values"]) == 2
    assert data["values"][0]["value"] == "acs_ecs_dashboard"
    assert data["values"][0]["count"] == 156
    assert data["total"] == 2
    assert data["limit"] == 20
    assert data["offset"] == 0


def test_field_values_schema_empty():
    """测试 FieldValuesResponse Schema 空值"""
    from apps.rule.schemas import FieldValuesResponse, FieldValueItem

    resp = FieldValuesResponse(
        field="labels.cluster",
        values=[],
        total=0,
        limit=20,
        offset=0,
    )
    data = resp.model_dump()

    assert data["field"] == "labels.cluster"
    assert data["values"] == []
    assert data["total"] == 0


def test_supported_fields():
    """测试支持的字段路径常量"""
    from apps.rule.routers import SUPPORTED_SIMPLE_FIELDS

    # 简单字段
    assert "namespace" in SUPPORTED_SIMPLE_FIELDS
    assert "source" in SUPPORTED_SIMPLE_FIELDS
    assert "metric_name" in SUPPORTED_SIMPLE_FIELDS
    assert "instance_id" in SUPPORTED_SIMPLE_FIELDS
    assert "instance_name" in SUPPORTED_SIMPLE_FIELDS
    assert "status" in SUPPORTED_SIMPLE_FIELDS

    # 不支持的字段
    assert "title" not in SUPPORTED_SIMPLE_FIELDS
    assert "content" not in SUPPORTED_SIMPLE_FIELDS
    assert "raw_data" not in SUPPORTED_SIMPLE_FIELDS


def test_status_field_values():
    """测试 status 固定枚举值"""
    from apps.rule.routers import _get_status_field_values, STATUS_CHINESE_LABELS

    resp = asyncio.run(_get_status_field_values(search="", limit=10, offset=0))
    values = [v.value for v in resp.values]

    assert "firing" in values
    assert "resolved" in values
    assert "suppressed" in values
    assert "acknowledged" in values
    assert resp.total == 4

    # 搜索过滤
    resp = asyncio.run(_get_status_field_values(search="触发", limit=10, offset=0))
    assert resp.total == 1
    assert resp.values[0].value == "firing"


def test_status_chinese_labels():
    """测试 status 中文标签映射"""
    from apps.rule.routers import STATUS_CHINESE_LABELS

    assert STATUS_CHINESE_LABELS["firing"] == "触发中"
    assert STATUS_CHINESE_LABELS["resolved"] == "已恢复"
    assert STATUS_CHINESE_LABELS["suppressed"] == "已抑制"
    assert STATUS_CHINESE_LABELS["acknowledged"] == "已确认"


def _make_alert(**kwargs) -> Alert:
    defaults = {
        "id": 1,
        "tenant_id": "1",
        "alert_key": "test-key",
        "fingerprint": "fp1",
        "source": "prometheus",
        "severity": "warning",
        "labels": {},
    }
    defaults.update(kwargs)
    return Alert(**defaults)


def _make_suppress_rule(suppress_config: dict, name: str = "suppress-test"):
    return SimpleNamespace(
        id=10,
        name=name,
        suppress_config=suppress_config,
    )


@pytest.mark.asyncio
async def test_check_suppress_rule_based_nested_conditions():
    """rule_based 嵌套 conditions 应触发抑制"""
    engine = RuleEngine()
    alert = _make_alert(severity="warning")
    rule = _make_suppress_rule({
        "enabled": True,
        "type": "rule_based",
        "rule_based": {
            "conditions": [{"field": "severity", "operator": "eq", "value": "warning"}],
        },
    })

    with patch.object(engine, "_find_matching_suppress_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_suppressed, reason, _ = await engine._check_suppress(
            db=None, redis=None, alert=alert, trace_id="trace-1"
        )

    assert is_suppressed is True
    assert reason and "触发规则抑制" in reason


def test_get_suppress_rule_conditions_prefers_rule_level():
    """条件以 rule.conditions 为准，不与 suppress_config 重复评估"""
    engine = RuleEngine()
    rule = _make_suppress_rule({
        "enabled": True,
        "rule_based": {"conditions": [{"field": "severity", "operator": "eq", "value": "low"}]},
    })
    rule.conditions = [{"field": "severity", "operator": "eq", "value": "high"}]
    rule.condition_mode = "and"
    conditions, mode = engine._get_suppress_rule_conditions(rule)
    assert conditions[0]["value"] == "high"
    assert mode == "and"


def test_get_suppress_rule_conditions_legacy_fallback():
    """兼容仅写在 suppress_config.rule_based 内的旧条件"""
    engine = RuleEngine()
    rule = _make_suppress_rule({
        "enabled": True,
        "rule_based": {"conditions": [{"field": "severity", "operator": "eq", "value": "warning"}]},
    })
    rule.conditions = []
    rule.condition_mode = "and"
    conditions, _ = engine._get_suppress_rule_conditions(rule)
    assert conditions[0]["value"] == "warning"


@pytest.mark.asyncio
async def test_check_suppress_rule_based_legacy_top_level_conditions():
    """兼容顶层 conditions 的旧配置格式"""
    engine = RuleEngine()
    alert = _make_alert(severity="critical")
    rule = _make_suppress_rule({
        "enabled": True,
        "type": "rule_based",
        "conditions": [{"field": "severity", "operator": "eq", "value": "critical"}],
        "condition_mode": "and",
    })

    with patch.object(engine, "_find_matching_suppress_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_suppressed, reason, _ = await engine._check_suppress(
            db=None, redis=None, alert=alert, trace_id="trace-2"
        )

    assert is_suppressed is True
    assert reason and "触发规则抑制" in reason


@pytest.mark.asyncio
async def test_check_suppress_legacy_maintenance_window_type_uses_rule_based():
    """旧 type=maintenance_window 的配置仍按 rule_based 条件评估"""
    engine = RuleEngine()
    alert = _make_alert(severity="high", source="prometheus")
    rule = _make_suppress_rule({
        "enabled": True,
        "type": "maintenance_window",
        "rule_based": {
            "conditions": [{"field": "severity", "operator": "eq", "value": "high"}],
        },
    })

    with patch.object(engine, "_find_matching_suppress_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_suppressed, reason, _ = await engine._check_suppress(
            db=None, redis=None, alert=alert, trace_id="trace-3"
        )

    assert is_suppressed is True
    assert reason and "触发规则抑制" in reason


def test_compute_suppress_effective_until_zero_is_none():
    assert compute_suppress_effective_until(0) is None


def test_enrich_suppress_config_writes_effective_until():
    cfg = enrich_suppress_config({"enabled": True, "duration_minutes": 60})
    assert cfg["duration_minutes"] == 60
    assert cfg["effective_until"] is not None
    until = datetime.fromisoformat(cfg["effective_until"].replace("Z", "+00:00"))
    assert until > datetime.now(timezone.utc)


def test_is_suppress_rule_in_effect_permanent():
    ok, msg = is_suppress_rule_in_effect({"duration_minutes": 0})
    assert ok is True
    assert "永久" in msg


def test_is_suppress_rule_in_effect_within_window():
    until = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    ok, _ = is_suppress_rule_in_effect({"duration_minutes": 30, "effective_until": until})
    assert ok is True


def test_is_suppress_rule_in_effect_expired():
    until = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    ok, msg = is_suppress_rule_in_effect({"duration_minutes": 5, "effective_until": until})
    assert ok is False
    assert "过期" in msg


def test_is_suppress_rule_in_effect_legacy_created_at_fallback():
    created = datetime.now(timezone.utc) - timedelta(minutes=10)
    ok, _ = is_suppress_rule_in_effect(
        {"duration_minutes": 60},
        rule_created_at=created,
    )
    assert ok is True


@pytest.mark.asyncio
async def test_check_suppress_skips_expired_rule():
    engine = RuleEngine()
    alert = _make_alert(severity="warning")
    until = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    rule = _make_suppress_rule({
        "enabled": True,
        "duration_minutes": 5,
        "effective_until": until,
    })

    with patch.object(engine, "_find_matching_suppress_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_suppressed, _, _ = await engine._check_suppress(
            db=None, redis=None, alert=alert, trace_id="trace-expired"
        )

    assert is_suppressed is False


@pytest.mark.asyncio
async def test_check_suppress_active_window():
    engine = RuleEngine()
    alert = _make_alert(severity="warning")
    until = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    rule = _make_suppress_rule({
        "enabled": True,
        "duration_minutes": 30,
        "effective_until": until,
    })

    with patch.object(engine, "_find_matching_suppress_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_suppressed, reason, _ = await engine._check_suppress(
            db=None, redis=None, alert=alert, trace_id="trace-active"
        )

    assert is_suppressed is True
    assert reason and "触发规则抑制" in reason


def test_strategy_rule_response_maps_suppress_config():
    """StrategyRuleResponse 应将 suppress_config 映射为 config"""
    from apps.rule.models import AlertRule
    from apps.rule.schemas import StrategyRuleResponse

    now = datetime.now(timezone.utc)
    rule = AlertRule(
        tenant_id="1",
        name="抑制规则",
        code="_suppress_test",
        priority=10,
        is_active=True,
        suppress_config={"enabled": True, "type": "rule_based"},
        created_at=now,
        updated_at=now,
    )
    rule.id = 99

    resp = StrategyRuleResponse.from_alert_rule(rule, config_field="suppress_config")
    assert resp.config == rule.suppress_config
    assert resp.id == 99
    assert resp.name == "抑制规则"
    assert resp.suppress_in_effect is True


def test_strategy_rule_response_suppress_expired():
    from apps.rule.models import AlertRule
    from apps.rule.schemas import StrategyRuleResponse

    now = datetime.now(timezone.utc)
    until = (now - timedelta(minutes=1)).isoformat()
    rule = AlertRule(
        tenant_id="1",
        name="过期抑制",
        code="_suppress_expired",
        priority=10,
        is_active=True,
        suppress_config={
            "enabled": True,
            "duration_minutes": 5,
            "effective_until": until,
        },
        created_at=now,
        updated_at=now,
    )
    rule.id = 100
    resp = StrategyRuleResponse.from_alert_rule(rule, config_field="suppress_config")
    assert resp.suppress_in_effect is False

