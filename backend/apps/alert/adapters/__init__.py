"""
SentinelX - 告警适配器
"""
from .base import AlertAdapter
from .factory import AdapterFactory
from .prometheus import PrometheusAdapter, PrometheusMetricsAdapter
from .zabbix import ZabbixAdapter
from .aliyun import AlibabaCloudAdapter
from .aliyun_cms import AliyunCmsAdapter
from .aliyun_cms2 import AliyunCms2Adapter
from .tencent import TencentCloudAdapter
from .custom import CustomWebhookAdapter

__all__ = [
    "AlertAdapter",
    "AdapterFactory",
    "PrometheusAdapter",
    "PrometheusMetricsAdapter",
    "ZabbixAdapter",
    "AlibabaCloudAdapter",
    "AliyunCmsAdapter",
    "AliyunCms2Adapter",
    "TencentCloudAdapter",
    "CustomWebhookAdapter",
]
