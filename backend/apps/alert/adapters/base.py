"""
SentinelX - 告警适配器基类
"""
import hashlib
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from apps.alert.schemas import AlertCreate


class AlertAdapter(ABC):
    """告警适配器基类 - 策略模式"""

    def __init__(self):
        self.source_type = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def parse(self, raw_data: Dict[str, Any], tenant_id: str) -> Optional[AlertCreate]:
        """
        解析原始告警数据为标准AlertCreate格式
        返回None表示该数据不适用于此适配器
        """
        pass

    async def validate(self, raw_data: Dict[str, Any]) -> bool:
        """验证数据是否适用于此适配器"""
        return True

    def generate_fingerprint(self, alert_key: str, source: str, labels: Dict[str, Any]) -> str:
        """生成告警指纹"""
        fp_data = {
            "source": source,
            "alert_key": alert_key,
            "labels": json.dumps(labels, sort_keys=True, default=str),
        }
        fp_json = json.dumps(fp_data, sort_keys=True, default=str)
        return hashlib.sha256(fp_json.encode()).hexdigest()[:16]
