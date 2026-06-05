"""Tests for alert response helpers."""
from datetime import datetime, timezone

from apps.alert.models import Alert
from apps.alert.services.alert_utils import build_alert_response


def _make_alert(**kwargs) -> Alert:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": 1,
        "tenant_id": "1",
        "alert_key": "test-key",
        "fingerprint": "fp",
        "source": "aliyun_cms",
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


def test_build_alert_response_includes_source_name():
    alert = _make_alert(source_id=10)
    response = build_alert_response(alert, "生产环境云监控")
    assert response.source == "aliyun_cms"
    assert response.source_name == "生产环境云监控"


def test_build_alert_response_without_source_name():
    alert = _make_alert(id=2, alert_key="test-key-2", fingerprint="fp2", source="prometheus", severity="medium")
    response = build_alert_response(alert, None)
    assert response.source == "prometheus"
    assert response.source_name is None
