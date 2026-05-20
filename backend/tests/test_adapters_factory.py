"""AdapterFactory 与 AlertSourceType 一致性测试"""
from apps.alert.adapters.factory import AdapterFactory
from apps.alert.adapters.prometheus import PrometheusAdapter
from apps.alert.adapters.custom import CustomWebhookAdapter
from apps.alert.adapters.aliyun_cms2 import AliyunCms2Adapter
from apps.core.constants import AlertSourceType


def test_grafana_uses_prometheus_adapter():
    adapter = AdapterFactory.get_adapter("grafana")
    assert isinstance(adapter, PrometheusAdapter)


def test_huawei_uses_custom_adapter():
    adapter = AdapterFactory.get_adapter("huawei")
    assert isinstance(adapter, CustomWebhookAdapter)


def test_aliyun_cms2_adapter():
    adapter = AdapterFactory.get_adapter("aliyun_cms2")
    assert isinstance(adapter, AliyunCms2Adapter)


def test_alert_source_type_includes_aliyun_cms2():
    assert AlertSourceType.is_valid("aliyun_cms2")
    assert AlertSourceType.is_valid("grafana")
    assert AlertSourceType.is_valid("huawei")


def test_aliyun_cms2_webhook_path():
    path = AlertSourceType.WEBHOOK_PATHS[AlertSourceType.ALIYUN_CMS2]
    assert "aliyun_cms2" in path
