"""
SentinelX - 适配器工厂
"""
from typing import Dict, Any
from .base import AlertAdapter
from .prometheus import PrometheusAdapter, PrometheusMetricsAdapter
from .zabbix import ZabbixAdapter
from .aliyun import AlibabaCloudAdapter
from .aliyun_cms import AliyunCmsAdapter
from .aliyun_cms2 import AliyunCms2Adapter
from .tencent import TencentCloudAdapter
from .custom import CustomWebhookAdapter


class AdapterFactory:
    """适配器工厂"""

    _adapters = {
        "prometheus": PrometheusAdapter,
        "alertmanager": PrometheusAdapter,
        "grafana": PrometheusAdapter,  # Grafana 统一告警兼容 Prometheus/Alertmanager 格式
        "zabbix": ZabbixAdapter,
        "aliyun": AlibabaCloudAdapter,
        "aliyun_cms": AliyunCmsAdapter,
        "aliyun_cms2": AliyunCms2Adapter,
        "tencent": TencentCloudAdapter,
        "huawei": CustomWebhookAdapter,  # 暂用通用解析，见文档 webhook 字段约定
        "custom": CustomWebhookAdapter,
    }

    @classmethod
    def get_adapter(cls, source_type: str) -> AlertAdapter:
        """获取适配器"""
        adapter_class = cls._adapters.get(source_type.lower(), CustomWebhookAdapter)
        return adapter_class()

    @classmethod
    def auto_detect(cls, raw_data: Dict[str, Any]) -> AlertAdapter:
        """自动检测数据源类型"""
        if "aliyun_alert" in raw_data:
            return AlibabaCloudAdapter()
        if "appid" in raw_data or "dimension" in raw_data:
            return TencentCloudAdapter()
        if "host" in raw_data or "event" in raw_data:
            return ZabbixAdapter()
        if "alerts" in raw_data or ("labels" in raw_data and "annotations" in raw_data):
            return PrometheusAdapter()
        if "metric" in raw_data:
            return PrometheusMetricsAdapter()
        return CustomWebhookAdapter()
