"""实例告警聚合：实例识别 / 类型分类 / 分组测试"""
from datetime import datetime, timezone

from apps.alert.models import Alert
from apps.alert.services.alert_utils import extract_instance_from_title
from apps.alert.services.by_instance import (
    UNKNOWN_INSTANCE_KEY,
    classify_alert_type,
    extract_instance,
    filter_instance_alerts,
    group_alerts_by_instance,
    sort_instances,
)


def _make_alert(**kwargs) -> Alert:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": 1,
        "tenant_id": "1",
        "alert_key": "test-key",
        "fingerprint": "fp",
        "source": "lcmdb",
        "title": "CPU high",
        "severity": "high",
        "status": "firing",
        "labels": {},
        "annotations": {},
        "raw_data": {},
        "fire_count": 1,
        "repeat_count": 0,
        "escalation_count": 0,
        "matched_rules": [],
        "notification_channels": [],
        "fired_at": now,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Alert(**defaults)


def test_extract_instance_prefers_instance_name():
    alert = _make_alert(instance_name="文档生产服务器", instance_id="i-1", labels={"ip": "10.0.0.8"})
    info = extract_instance(alert)
    assert info["instance_key"] == "文档生产服务器"
    assert info["instance_name"] == "文档生产服务器"
    assert info["ip"] == "10.0.0.8"


def test_extract_instance_lcmdb_title_beats_ip():
    alert = _make_alert(
        title="文档生产服务器 的 [磁盘:Disk]",
        labels={"ip": "10.0.0.8"},
        alert_key="lcmdb-10.0.0.8-Disk",
    )
    info = extract_instance(alert)
    assert info["instance_key"] == "文档生产服务器"
    assert info["instance_name"] == "文档生产服务器"
    assert info["ip"] == "10.0.0.8"


def test_extract_instance_same_title_groups_together():
    a = _make_alert(
        id=1,
        title="文档生产服务器 的 [CPU:Usage]",
        labels={"ip": "10.0.0.8"},
        alert_key="lcmdb-10.0.0.8-CPU",
    )
    b = _make_alert(
        id=2,
        title="文档生产服务器 的 [磁盘:Disk]",
        labels={"ip": "10.0.0.8"},
        alert_key="lcmdb-10.0.0.8-Disk",
    )
    assert extract_instance(a)["instance_key"] == extract_instance(b)["instance_key"] == "文档生产服务器"


def test_extract_instance_from_title_lcmdb():
    assert extract_instance_from_title("企业知识库-测试环境 的 [磁盘:Disk]") == "企业知识库-测试环境"


def test_extract_instance_unknown():
    alert = _make_alert(title="some alert", labels={})
    info = extract_instance(alert)
    assert info["instance_key"] == UNKNOWN_INSTANCE_KEY
    assert info["instance_name"] is None


def test_classify_cpu_memory_disk():
    assert classify_alert_type(_make_alert(title="CPU 使用率过高", alert_key="cpu_high"))[0] == "cpu"
    assert classify_alert_type(_make_alert(title="内存不足", metric_name="mem_usage"))[0] == "memory"
    assert classify_alert_type(_make_alert(title="磁盘空间不足", alert_key="lcmdb-1.1.1.1-Disk"))[0] == "disk"


def test_classify_process_and_network_and_other():
    assert classify_alert_type(_make_alert(title="进程 foundation-api.jar 停止", alert_key="lcmdb-ip-进程-foundation-api.jar"))[0] == "process"
    assert classify_alert_type(_make_alert(title="网络流量异常", metric_name="network_in"))[0] == "network"
    assert classify_alert_type(_make_alert(title="未知业务异常", alert_key="biz-error"))[0] == "other"


def test_classify_avoids_false_positives():
    # amount 不应命中 mount/存储；method 不应命中网络；program 不应命中 ram
    assert classify_alert_type(_make_alert(title="订单 amount 校验失败", alert_key="biz-amount"))[0] == "other"
    assert classify_alert_type(_make_alert(title="method timeout", alert_key="api-method-timeout"))[0] == "other"
    assert classify_alert_type(_make_alert(title="Program error", alert_key="app-program-error"))[0] == "other"


def test_classify_common_metric_names():
    assert classify_alert_type(_make_alert(title="入向流量异常", metric_name="net_in"))[0] == "network"
    assert classify_alert_type(_make_alert(title="内存使用过高", metric_name="mem_used"))[0] == "memory"
    assert classify_alert_type(_make_alert(title="资源使用偏高", metric_name="memory_usage"))[0] == "memory"
    assert classify_alert_type(_make_alert(title="mount_usage 超阈值", alert_key="mount_usage"))[0] == "disk"
    assert classify_alert_type(_make_alert(title="java_down", alert_key="java_down"))[0] == "process"
    assert classify_alert_type(_make_alert(title="服务异常", metric_name="process_count"))[0] == "process"


def test_sort_instances_max_severity_desc_puts_critical_first():
    items = [
        {"instance_key": "a", "alert_count": 1, "max_severity": "medium", "last_fired_at": None},
        {"instance_key": "b", "alert_count": 1, "max_severity": "critical", "last_fired_at": None},
        {"instance_key": "c", "alert_count": 1, "max_severity": "info", "last_fired_at": None},
    ]
    sorted_desc = sort_instances(items, sort_by="max_severity", sort_order="desc")
    assert [i["instance_key"] for i in sorted_desc] == ["b", "a", "c"]
    sorted_asc = sort_instances(items, sort_by="max_severity", sort_order="asc")
    assert sorted_asc[0]["instance_key"] == "c"
    assert sorted_asc[-1]["instance_key"] == "b"


def test_sort_instances_last_fired_at():
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 6, 1, tzinfo=timezone.utc)
    items = [
        {"instance_key": "old", "alert_count": 1, "max_severity": "info", "last_fired_at": older},
        {"instance_key": "new", "alert_count": 1, "max_severity": "info", "last_fired_at": newer},
        {"instance_key": "none", "alert_count": 1, "max_severity": "info", "last_fired_at": None},
    ]
    sorted_desc = sort_instances(items, sort_by="last_fired_at", sort_order="desc")
    assert [i["instance_key"] for i in sorted_desc] == ["new", "old", "none"]


def test_classify_priority_cpu_over_disk():
    # 标题同时含 CPU 与 磁盘 时，CPU 优先
    code, _ = classify_alert_type(_make_alert(title="CPU 与磁盘 状态异常"))
    assert code == "cpu"


def test_group_alerts_by_instance():
    alerts = [
        _make_alert(
            id=1,
            title="CPU high",
            instance_name="文档生产服务器",
            severity="critical",
            status="firing",
        ),
        _make_alert(
            id=2,
            title="磁盘空间不足",
            instance_name="文档生产服务器",
            alert_key="disk-full",
            severity="high",
            status="firing",
        ),
        _make_alert(
            id=3,
            title="内存不足",
            instance_name="应用服务器",
            metric_name="memory_usage",
            severity="medium",
            status="resolved",
            fired_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]
    groups = group_alerts_by_instance(alerts)
    by_key = {g["instance_key"]: g for g in groups}
    assert set(by_key) == {"文档生产服务器", "应用服务器"}

    doc = by_key["文档生产服务器"]
    assert doc["alert_count"] == 2
    assert doc["firing_count"] == 2
    assert doc["max_severity"] == "critical"
    type_codes = {t["type"]: t for t in doc["types"]}
    assert "cpu" in type_codes
    assert "disk" in type_codes
    assert type_codes["cpu"]["count"] == 1


def test_sort_instances_by_count():
    items = [
        {"instance_key": "a", "alert_count": 1, "max_severity": "info", "last_fired_at": None},
        {"instance_key": "b", "alert_count": 5, "max_severity": "high", "last_fired_at": None},
    ]
    sorted_items = sort_instances(items, sort_by="alert_count", sort_order="desc")
    assert sorted_items[0]["instance_key"] == "b"


def test_filter_instance_alerts_by_type():
    alerts = [
        _make_alert(id=1, title="CPU high", instance_name="host-a"),
        _make_alert(id=2, title="disk full", instance_name="host-a", alert_key="disk"),
        _make_alert(id=3, title="CPU high", instance_name="host-b"),
    ]
    matched = filter_instance_alerts(alerts, "host-a", "cpu")
    assert len(matched) == 1
    assert matched[0].id == 1
