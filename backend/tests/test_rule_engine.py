"""
SentinelX - 规则引擎测试
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apps.rule.engine import RuleEngine
from apps.rule.suppress_timing import (
    compute_suppress_effective_until,
    enrich_suppress_config,
    is_suppress_rule_in_effect,
)
from apps.alert.models import Alert, AlertAggregateGroup, AlertAggregateMember


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


def test_evaluate_conditions_source_id_in_accepts_string_values_from_ui():
    """页面保存的 source_id 字符串列表应能匹配整数告警字段"""
    engine = RuleEngine()
    conditions = [{"field": "source_id", "operator": "in", "value": ["3"]}]
    alert_data = {"source_id": 3}

    matched, reason, _ = engine.evaluate_conditions(conditions, "and", alert_data)

    assert matched is True
    assert reason is None


def test_evaluate_conditions_legacy_source_field_with_numeric_id():
    """去重/聚合 UI 曾存 field=source + 数字 ID，应匹配 source_id"""
    engine = RuleEngine()
    conditions = [{"field": "source", "operator": "in", "value": [3]}]
    alert_data = {"source": "aliyun_cms", "source_id": 3}

    matched, reason, _ = engine.evaluate_conditions(conditions, "and", alert_data)

    assert matched is True
    assert reason is None


def test_is_effective_dedup_config_rejects_json_null_and_disabled():
    from apps.rule.engine import _is_effective_dedup_config

    assert _is_effective_dedup_config(None) is False
    assert _is_effective_dedup_config({"enabled": False}) is False
    assert _is_effective_dedup_config({"enabled": True, "dedup_type": "fingerprint"}) is True


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


@pytest.mark.asyncio
async def test_status_field_values():
    """测试 status 固定枚举值"""
    from apps.rule.routers import _get_status_field_values, STATUS_CHINESE_LABELS

    resp = await _get_status_field_values(search="", limit=10, offset=0)
    values = [v.value for v in resp.values]

    assert "firing" in values
    assert "resolved" in values
    assert "suppressed" in values
    assert "acknowledged" in values
    assert resp.total == 4

    # 搜索过滤
    resp = await _get_status_field_values(search="触发", limit=10, offset=0)
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


def _make_dedup_rule(dedup_config: dict, name: str = "dedup-test", rule_id: int = 20):
    rule = SimpleNamespace(
        id=rule_id,
        name=name,
        deduplication_config=dedup_config,
        conditions=[],
        condition_mode="and",
    )
    return rule


@pytest.mark.asyncio
async def test_check_dedup_blocks_second_alert_with_same_fingerprint_fields():
    """窗口内第二条相同指纹告警应被去重"""
    engine = RuleEngine()
    alert = _make_alert(id=2, alert_key="same-key")
    rule = _make_dedup_rule({
        "enabled": True,
        "dedup_type": "fingerprint",
        "fingerprint_fields": ["alert_key"],
        "window_seconds": 300,
    })

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"1")

    with patch.object(engine, "_find_matching_dedup_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_duplicate, _, duplicate_of = await engine._check_dedup(
            db=None, redis=redis, alert=alert, trace_id="trace-dedup-1"
        )

    assert is_duplicate is True
    assert duplicate_of == "1"


@pytest.mark.asyncio
async def test_check_dedup_allows_mq_redelivery_of_same_alert():
    """MQ 重投同一告警时不应因 Redis 键指向自身而误判重复"""
    engine = RuleEngine()
    alert = _make_alert(id=42, alert_key="same-key")
    rule = _make_dedup_rule({
        "enabled": True,
        "dedup_type": "fingerprint",
        "fingerprint_fields": ["alert_key"],
        "window_seconds": 300,
    })

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"42")
    redis.set = AsyncMock()

    with patch.object(engine, "_find_matching_dedup_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_duplicate, _, duplicate_of = await engine._check_dedup(
            db=None, redis=redis, alert=alert, trace_id="trace-dedup-redelivery"
        )

    assert is_duplicate is False
    assert duplicate_of is None
    redis.set.assert_not_awaited()


def test_stable_hash_is_deterministic():
    from apps.rule.engine import _stable_hash

    assert _stable_hash("severity:eq:high") == _stable_hash("severity:eq:high")
    assert _stable_hash("a") != _stable_hash("b")


@pytest.mark.asyncio
async def test_check_dedup_increments_match_count_when_blocking():
    engine = RuleEngine()
    alert = _make_alert(id=2, alert_key="same-key")
    rule = _make_dedup_rule({
        "enabled": True,
        "dedup_type": "fingerprint",
        "fingerprint_fields": ["alert_key"],
        "window_seconds": 300,
    })
    rule.match_count = 0

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"1")
    db = AsyncMock()
    db.commit = AsyncMock()

    with patch.object(engine, "_find_matching_dedup_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_duplicate, _, _ = await engine._check_dedup(
            db=db, redis=redis, alert=alert, trace_id="trace-dedup-count"
        )

    assert is_duplicate is True
    assert rule.match_count == 1
    assert rule.last_match_at is not None
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_check_dedup_increments_match_count_when_establishing_window():
    engine = RuleEngine()
    alert = _make_alert(id=1, alert_key="new-key")
    rule = _make_dedup_rule({
        "enabled": True,
        "dedup_type": "fingerprint",
        "fingerprint_fields": ["alert_key"],
        "window_seconds": 300,
    })
    rule.match_count = 2

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    db = AsyncMock()
    db.commit = AsyncMock()

    with patch.object(engine, "_find_matching_dedup_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_duplicate, _, _ = await engine._check_dedup(
            db=db, redis=redis, alert=alert, trace_id="trace-dedup-window"
        )

    assert is_duplicate is False
    assert rule.match_count == 3
    db.commit.assert_awaited()


def _mock_dedup_rules_db(rules: list):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rules
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.mark.asyncio
async def test_find_matching_dedup_rules_condition_mode_ignores_rule_conditions():
    """条件模式：不因 rule.conditions 不匹配而排除规则"""
    engine = RuleEngine()
    alert = _make_alert(severity="high")
    rule = _make_dedup_rule(
        {
            "enabled": True,
            "dedup_type": "condition",
            "conditions": [{"field": "severity", "operator": "eq", "value": "high"}],
            "condition_mode": "and",
            "window_seconds": 300,
        },
        rule_id=1,
    )
    rule.conditions = [{"field": "severity", "operator": "eq", "value": "low"}]

    matched = await engine._find_matching_dedup_rules(_mock_dedup_rules_db([rule]), alert)
    assert len(matched) == 1
    assert matched[0].id == 1


@pytest.mark.asyncio
async def test_find_matching_dedup_rules_fingerprint_mode_uses_rule_conditions():
    """指纹模式：规则级触发条件仍生效"""
    engine = RuleEngine()
    alert = _make_alert(severity="high")
    rule_match = _make_dedup_rule(
        {
            "enabled": True,
            "dedup_type": "fingerprint",
            "fingerprint_fields": ["alert_key"],
            "window_seconds": 300,
        },
        rule_id=1,
    )
    rule_match.conditions = [{"field": "severity", "operator": "eq", "value": "high"}]
    rule_no_match = _make_dedup_rule(
        {
            "enabled": True,
            "dedup_type": "fingerprint",
            "fingerprint_fields": ["alert_key"],
            "window_seconds": 300,
        },
        rule_id=2,
    )
    rule_no_match.conditions = [{"field": "severity", "operator": "eq", "value": "low"}]

    matched = await engine._find_matching_dedup_rules(
        _mock_dedup_rules_db([rule_match, rule_no_match]), alert
    )
    assert len(matched) == 1
    assert matched[0].id == 1


@pytest.mark.asyncio
async def test_find_matching_dedup_rules_condition_mode_empty_config_conditions_skipped():
    """条件模式：config.conditions 为空时不进入候选"""
    engine = RuleEngine()
    alert = _make_alert()
    rule = _make_dedup_rule(
        {
            "enabled": True,
            "dedup_type": "condition",
            "conditions": [],
            "condition_mode": "and",
            "window_seconds": 300,
        },
    )

    matched = await engine._find_matching_dedup_rules(_mock_dedup_rules_db([rule]), alert)
    assert matched == []


@pytest.mark.asyncio
async def test_check_dedup_condition_mode_cohort_bucket():
    """条件模式：满足同一组 config 条件的告警共用一个去重桶"""
    engine = RuleEngine()
    alert1 = _make_alert(id=1, alert_key="key-a", labels={"dedup_tag": "batch-a"})
    alert2 = _make_alert(id=2, alert_key="key-b", labels={"dedup_tag": "batch-a"})
    rule = _make_dedup_rule(
        {
            "enabled": True,
            "dedup_type": "condition",
            "conditions": [{"field": "labels.dedup_tag", "operator": "eq", "value": "batch-a"}],
            "condition_mode": "and",
            "window_seconds": 300,
        },
    )

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    db = AsyncMock()
    db.commit = AsyncMock()

    with patch.object(engine, "_find_matching_dedup_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        is_dup1, _, _ = await engine._check_dedup(
            db=db, redis=redis, alert=alert1, trace_id="trace-cohort-1"
        )
        assert is_dup1 is False

        redis.get = AsyncMock(return_value=b"1")
        is_dup2, _, duplicate_of = await engine._check_dedup(
            db=db, redis=redis, alert=alert2, trace_id="trace-cohort-2"
        )
        assert is_dup2 is True
        assert duplicate_of == "1"


def _make_aggregate_rule(aggregate_config: dict, name: str = "aggregate-test", rule_id: int = 30):
    rule = SimpleNamespace(
        id=rule_id,
        name=name,
        aggregate_config=aggregate_config,
        conditions=[],
        condition_mode="and",
    )
    return rule


def _mock_aggregate_rules_db(rules: list):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rules
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.mark.asyncio
async def test_find_matching_aggregate_rules_condition_mode_ignores_rule_conditions():
    """条件模式：不因 rule.conditions 不匹配而排除规则"""
    engine = RuleEngine()
    alert = _make_alert(severity="high")
    rule = _make_aggregate_rule(
        {
            "enabled": True,
            "mode": "condition",
            "conditions": [{"field": "severity", "operator": "eq", "value": "high"}],
            "condition_mode": "and",
            "window_seconds": 300,
        },
        rule_id=1,
    )
    rule.conditions = [{"field": "severity", "operator": "eq", "value": "low"}]

    matched = await engine._find_matching_aggregate_rules(_mock_aggregate_rules_db([rule]), alert)
    assert len(matched) == 1
    assert matched[0].id == 1


@pytest.mark.asyncio
async def test_find_matching_aggregate_rules_group_by_mode_uses_rule_conditions():
    """分组模式：规则级触发条件仍生效"""
    engine = RuleEngine()
    alert = _make_alert(severity="high")
    rule_match = _make_aggregate_rule(
        {
            "enabled": True,
            "mode": "group_by",
            "group_by": ["alert_key", "source"],
            "window_seconds": 300,
        },
        rule_id=1,
    )
    rule_match.conditions = [{"field": "severity", "operator": "eq", "value": "high"}]
    rule_no_match = _make_aggregate_rule(
        {
            "enabled": True,
            "mode": "group_by",
            "group_by": ["alert_key"],
            "window_seconds": 300,
        },
        rule_id=2,
    )
    rule_no_match.conditions = [{"field": "severity", "operator": "eq", "value": "low"}]

    matched = await engine._find_matching_aggregate_rules(
        _mock_aggregate_rules_db([rule_match, rule_no_match]), alert
    )
    assert len(matched) == 1
    assert matched[0].id == 1


@pytest.mark.asyncio
async def test_find_matching_aggregate_rules_condition_mode_empty_config_conditions_skipped():
    """条件模式：config.conditions 为空时不进入候选"""
    engine = RuleEngine()
    alert = _make_alert()
    rule = _make_aggregate_rule(
        {
            "enabled": True,
            "mode": "condition",
            "conditions": [],
            "condition_mode": "and",
            "window_seconds": 300,
        },
    )

    matched = await engine._find_matching_aggregate_rules(_mock_aggregate_rules_db([rule]), alert)
    assert matched == []


@pytest.mark.asyncio
async def test_find_matching_aggregate_rules_ignores_json_null_config():
    """路由规则 aggregate_config 为 JSON null 时不应参与聚合匹配"""
    engine = RuleEngine()
    alert = _make_alert(severity="critical")
    rule_null = _make_aggregate_rule(None, name="route-null", rule_id=1)
    rule_null.aggregate_config = None  # ORM 读取 JSON null 的结果
    rule_effective = _make_aggregate_rule(
        {
            "enabled": True,
            "mode": "group_by",
            "group_by": ["alert_key"],
            "window_seconds": 300,
        },
        rule_id=18,
    )

    matched = await engine._find_matching_aggregate_rules(
        _mock_aggregate_rules_db([rule_null, rule_effective]), alert
    )
    assert len(matched) == 1
    assert matched[0].id == 18


@pytest.mark.asyncio
async def test_check_aggregate_creates_new_group():
    """分组模式：首条告警创建新聚合组"""
    engine = RuleEngine()
    alert = _make_alert(id=1, alert_key="agg-key", source="prometheus")
    rule = _make_aggregate_rule(
        {
            "enabled": True,
            "mode": "group_by",
            "group_by": ["alert_key", "source"],
            "window_seconds": 300,
            "max_count": 100,
            "store_original_alerts": True,
            "notify_policy": "parent_only",
        },
    )

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    db = AsyncMock()
    db.add = MagicMock()

    async def _flush():
        for call in db.add.call_args_list:
            obj = call[0][0]
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                obj.id = 10

    db.flush = AsyncMock(side_effect=_flush)
    db.commit = AsyncMock()

    with patch.object(engine, "_find_matching_aggregate_rules", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = [rule]
        agg_info, steps = await engine._check_aggregate(
            db=db, redis=redis, alert=alert, trace_id="trace-agg-new"
        )

    assert agg_info is not None
    assert agg_info.get("new_group") is True
    assert any(s.get("status") == "new_group" for s in steps)
    redis.set.assert_awaited()


@pytest.mark.asyncio
async def test_check_aggregate_joins_existing_group():
    """分组模式：相同分组键加入已有聚合组"""
    engine = RuleEngine()
    alert = _make_alert(id=2, alert_key="agg-key", source="prometheus")
    rule = _make_aggregate_rule(
        {
            "enabled": True,
            "mode": "group_by",
            "group_by": ["alert_key", "source"],
            "window_seconds": 300,
            "max_count": 100,
            "store_original_alerts": True,
            "notify_policy": "parent_only",
        },
    )

    group = SimpleNamespace(id=10, alert_count=1, tenant_id="1")

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"1")

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch.object(engine, "_find_matching_aggregate_rules", new_callable=AsyncMock) as mock_find, \
         patch.object(engine, "_resolve_aggregate_group_for_join", new_callable=AsyncMock) as mock_resolve:
        mock_find.return_value = [rule]
        mock_resolve.return_value = group
        agg_info, steps = await engine._check_aggregate(
            db=db, redis=redis, alert=alert, trace_id="trace-agg-join"
        )

    assert agg_info is not None
    assert agg_info["aggregated"] is True
    assert agg_info["parent_alert_id"] == 1
    assert agg_info["group_id"] == 10
    assert agg_info.get("notify_policy") == "parent_only"
    assert any(s.get("status") == "aggregated" for s in steps)
    mock_resolve.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_aggregate_group_prefers_parent_member_over_stale_groups():
    """同 group_key 存在多个历史组时，应通过 parent 成员关系命中当前组"""
    engine = RuleEngine()
    tenant_id = "1"
    aggregate_key = "aggregate:1:agg-key"
    now = datetime.now(timezone.utc)

    stale_group = AlertAggregateGroup(
        id=1,
        tenant_id=tenant_id,
        group_key=aggregate_key,
        alert_count=4,
        last_alert_at=now - timedelta(minutes=10),
    )
    active_group = AlertAggregateGroup(
        id=2,
        tenant_id=tenant_id,
        group_key=aggregate_key,
        alert_count=1,
        last_alert_at=now,
    )
    parent = Alert(id=86, tenant_id=tenant_id, aggregate_group_id=2)
    member = AlertAggregateMember(group_id=2, alert_id=86)

    db = AsyncMock()

    async def _get(model, pk):
        if model is Alert and pk == 86:
            return parent
        if model is AlertAggregateGroup and pk == 2:
            return active_group
        return None

    db.get = AsyncMock(side_effect=_get)

    member_result = MagicMock()
    member_result.scalars.return_value.first.return_value = member
    db.execute = AsyncMock(return_value=member_result)

    group = await engine._resolve_aggregate_group_for_join(
        db, tenant_id, aggregate_key, parent_alert_id=86, window_seconds=300
    )

    assert group is not None
    assert group.id == 2

