"""
SentinelX - 规则引擎测试
"""
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
