"""Tests for alert response helpers."""
from apps.alert.models import Alert
from apps.alert.services.alert_utils import build_alert_response


def test_build_alert_response_includes_source_name():
    alert = Alert(
        id=1,
        tenant_id="1",
        alert_key="test-key",
        fingerprint="fp",
        source="aliyun_cms",
        source_id=10,
        title="CPU high",
        severity="high",
        status="firing",
    )
    response = build_alert_response(alert, "生产环境云监控")
    assert response.source == "aliyun_cms"
    assert response.source_name == "生产环境云监控"


def test_build_alert_response_without_source_name():
    alert = Alert(
        id=2,
        tenant_id="1",
        alert_key="test-key-2",
        fingerprint="fp2",
        source="prometheus",
        title="Disk full",
        severity="medium",
        status="firing",
    )
    response = build_alert_response(alert, None)
    assert response.source == "prometheus"
    assert response.source_name is None
