"""
SentinelX - 规则引擎测试
"""
import asyncio
import pytest
from apps.rule.engine import RuleEngine


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
    from apps.rule.routers import SUPPORTED_SIMPLE_FIELDS, SUPPORTED_LABEL_PATHS

    # 简单字段
    assert "namespace" in SUPPORTED_SIMPLE_FIELDS
    assert "source" in SUPPORTED_SIMPLE_FIELDS
    assert "metric_name" in SUPPORTED_SIMPLE_FIELDS
    assert "instance_id" in SUPPORTED_SIMPLE_FIELDS
    assert "instance_name" in SUPPORTED_SIMPLE_FIELDS
    assert "status" in SUPPORTED_SIMPLE_FIELDS

    # JSON标签字段
    assert "labels" in SUPPORTED_LABEL_PATHS
    assert "labels.cluster" in SUPPORTED_LABEL_PATHS
    assert "labels.env" in SUPPORTED_LABEL_PATHS
    assert "labels.service" in SUPPORTED_LABEL_PATHS

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

