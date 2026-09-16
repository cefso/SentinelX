"""回填脚本逻辑：不依赖真实 DB 的纯计算 + 需补列检测。"""
from datetime import datetime, timezone

from apps.alert.models import Alert
from apps.alert.services.by_instance import UNKNOWN_INSTANCE_KEY, apply_instance_denorm
from scripts.backfill_alert_instance_fields import _needs_backfill


def _alert(**kwargs) -> Alert:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": 1,
        "tenant_id": 1,
        "alert_key": "k",
        "fingerprint": "f",
        "source": "lcmdb",
        "title": "CPU high",
        "severity": "high",
        "status": "firing",
        "labels": {},
        "annotations": {},
        "raw_data": {},
        "fired_at": now,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Alert(**defaults)


def test_needs_backfill_predicate_is_or_null_columns():
    clauses = _needs_backfill()
    assert len(clauses) == 1


def test_backfill_apply_instance_denorm_idempotent():
    alert = _alert(title="文档生产服务器 的 [磁盘:Disk]", labels={"ip": "10.0.0.1"})
    apply_instance_denorm(alert)
    first = (alert.instance_key, alert.alert_type)
    apply_instance_denorm(alert)
    assert (alert.instance_key, alert.alert_type) == first
    assert first == ("文档生产服务器", "disk")

    bare = _alert(title="other", labels={})
    apply_instance_denorm(bare)
    assert bare.instance_key == UNKNOWN_INSTANCE_KEY
    assert bare.alert_type == "other"
