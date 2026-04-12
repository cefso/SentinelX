"""
SentinelX - 云产品指标同步服务
从告警中提取并同步云产品指标信息
"""
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from apps.alert.models import Alert, CloudProductMetric


# 命名空间到产品名称的映射
NAMESPACE_PRODUCT_MAP = {
    # 阿里云
    "acs_ecs_dashboard": "阿里云ECS",
    "acs_rds_dashboard": "阿里云RDS",
    "acs_server_monitor": "阿里云云监控",
    "acs_slb_dashboard": "阿里云SLB",
    "acs_vpc_dashboard": "阿里云VPC",
    "acs_redis_dashboard": "阿里云Redis",
    "acs_mongodb_dashboard": "阿里云MongoDB",
    "acs_oss_dashboard": "阿里云OSS",
    "acs_cdn_dashboard": "阿里云CDN",
    "acs_log_service": "阿里云日志服务",
    "acs_fc_dashboard": "阿里云函数计算",
    "acs_kvstore_dashboard": "阿里云KVStore",
    "acs_ots_dashboard": "阿里云表格存储",
    "acs_apigateway_dashboard": "阿里云API网关",
    "acs_mns_dashboard": "阿里云消息服务",
    "acs_elasticsearch_dashboard": "阿里云Elasticsearch",
    "acs_dataworks_dashboard": "阿里云DataWorks",
    "acs_maxcompute_dashboard": "阿里云MaxCompute",
    # 腾讯云 (通过 dimensions.namespace 区分)
    "qce/cvm": "腾讯云CVM",
    "qce/cdb": "腾讯云CDB",
    "qce/lb": "腾讯云CLB",
    "qce/redis": "腾讯云Redis",
    "qce/mongo": "腾讯云MongoDB",
    "qce/cos": "腾讯云COS",
    "qce/cdn": "腾讯云CDN",
    "qce/vpc": "腾讯云VPC",
    "qce/scf": "腾讯云SCF",
    "qce/cdn": "腾讯云CDN",
}


def get_product_name(source: str, namespace: str) -> str:
    """根据告警来源和命名空间确定产品名称"""
    # 阿里云
    if source in ("aliyun_cms", "aliyun_cms2", "aliyun"):
        if namespace in NAMESPACE_PRODUCT_MAP:
            return NAMESPACE_PRODUCT_MAP[namespace]
        # 通用: acs_xxx_dashboard -> 阿里云xxx
        if namespace.startswith("acs_"):
            product = namespace.replace("acs_", "").replace("_dashboard", "").replace("_", " ").title()
            return f"阿里云{product}"
        return f"阿里云{namespace}" if namespace else "阿里云"

    # 腾讯云
    if source == "tencent":
        if namespace in NAMESPACE_PRODUCT_MAP:
            return NAMESPACE_PRODUCT_MAP[namespace]
        return f"腾讯云{namespace}" if namespace else "腾讯云"

    # Prometheus/Alertmanager
    if source in ("prometheus", "alertmanager"):
        return namespace or "Prometheus"

    # Zabbix
    if source == "zabbix":
        return namespace or "Zabbix"

    return f"{source}: {namespace}" if namespace else source


def extract_namespace_metric(raw_data: Dict[str, Any], source: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[List]]:
    """
    从 raw_data 中提取 namespace, metric_name, unit, dimensions
    返回: (namespace, metric_name, unit, dimensions)
    """
    namespace = None
    metric_name = None
    unit = None
    dimensions = None

    if source in ("aliyun_cms", "aliyun_cms2", "aliyun"):
        # aliyun_cms: raw_data.namespace, raw_data.metricName, raw_data.unit, raw_data.dimensions
        namespace = raw_data.get("namespace", "")
        metric_name = raw_data.get("metricName", raw_data.get("rawMetricName", ""))
        unit = raw_data.get("unit", None)
        raw_dimensions = raw_data.get("dimensions", {})
        if isinstance(raw_dimensions, dict):
            dimensions = list(raw_dimensions.keys()) if raw_dimensions else []
        elif isinstance(raw_dimensions, list):
            dimensions = raw_dimensions

    elif source == "tencent":
        # tencent: raw_data.dimensions.namespace, raw_data.metricName, raw_data.metricUnit, raw_data.dimensions
        raw_dimensions = raw_data.get("dimensions", {})
        if isinstance(raw_dimensions, dict):
            namespace = raw_dimensions.get("namespace", "")
            # Extract dimensions keys, excluding namespace
            dimensions = [k for k in raw_dimensions.keys() if k != "namespace"]
        else:
            namespace = raw_data.get("namespace", "")
            dimensions = []
        metric_name = raw_data.get("metricName", "")
        unit = raw_data.get("metricUnit", None)

    elif source in ("prometheus", "alertmanager"):
        # prometheus: labels.namespace, labels.__name__, None, labels.dimensions
        labels = raw_data.get("labels", {})
        namespace = labels.get("namespace", labels.get("job", ""))
        metric_name = labels.get("__name__", labels.get("metric_name", ""))
        raw_dimensions = labels.get("dimensions", {})
        if isinstance(raw_dimensions, dict):
            dimensions = list(raw_dimensions.keys())
        elif isinstance(raw_dimensions, list):
            dimensions = raw_dimensions
        else:
            # For prometheus, collect all label keys except common ones
            dimensions = [k for k in labels.keys() if k not in ("namespace", "job", "__name__", "metric_name")]

    elif source == "zabbix":
        namespace = raw_data.get("host", "")
        metric_name = raw_data.get("metric_name", raw_data.get("name", ""))
        unit = raw_data.get("units", None)
        dimensions = []

    return namespace or None, metric_name or None, unit, dimensions


class SyncService:
    """云产品指标同步服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_metric(
        self,
        product: str,
        namespace: str,
        metric_name: str,
        metric_desc: Optional[str] = None,
        unit: Optional[str] = None,
        dimensions: Optional[List[Dict[str, Any]]] = None,
    ) -> CloudProductMetric:
        """
        插入或更新云产品指标记录
        如果记录存在且 metric_desc 为空，保留原有值
        """
        # 查找已存在的记录
        result = await self.db.execute(
            select(CloudProductMetric).where(
                and_(
                    CloudProductMetric.namespace == namespace,
                    CloudProductMetric.metric_name == metric_name,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 更新时保留用户编辑的 metric_desc
            if metric_desc and not existing.metric_desc:
                existing.metric_desc = metric_desc
            if unit and not existing.unit:
                existing.unit = unit
            if dimensions and not existing.dimensions:
                existing.dimensions = dimensions
            # 不重置 is_active，保留用户手动停用的状态
            await self.db.flush()
            return existing
        else:
            # 新建记录
            metric = CloudProductMetric(
                product=product,
                namespace=namespace,
                metric_name=metric_name,
                metric_desc=metric_desc,
                unit=unit,
                dimensions=dimensions or [],
                is_active=1,
            )
            self.db.add(metric)
            await self.db.flush()
            return metric

    async def sync_from_alerts(
        self,
        alert_ids: Optional[List[int]] = None,
        limit: int = 1000,
    ) -> Dict[str, int]:
        """
        从告警同步云产品指标

        Args:
            alert_ids: 指定告警ID列表（用于单条/少量同步）
            limit: 限制从最新告警中同步的数量（用于全量同步）

        Returns:
            同步统计: {"processed": N, "created": N, "updated": N, "skipped": N}
        """
        stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0}

        # 构建查询：只查询有 raw_data 和 namespace/metric_name 的告警
        # Use raw SQL for JSONB comparison since {} doesn't cast properly
        conditions = [
            text("raw_data IS NOT NULL AND raw_data != 'null'::jsonb AND raw_data != '{}'::jsonb"),
        ]

        if alert_ids:
            conditions.append(Alert.id.in_(alert_ids))
        else:
            # 全量同步：从各来源的最新告警中提取
            conditions.append(Alert.namespace.isnot(None))

        result = await self.db.execute(
            select(Alert)
            .where(and_(*conditions))
            .order_by(Alert.id.desc())
            .limit(limit)
        )
        alerts = result.scalars().all()

        seen_keys = set()  # 避免同一条告警内重复处理
        for alert in alerts:
            namespace, metric_name, unit, dimensions = extract_namespace_metric(alert.raw_data, alert.source)

            if not namespace and not metric_name:
                stats["skipped"] += 1
                continue

            # 跳过告警源标签缺失的情况
            if not namespace:
                namespace = alert.namespace or ""

            # 生成唯一键用于去重
            key = f"{alert.source}:{namespace}:{metric_name}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            product = get_product_name(alert.source, namespace)
            metric = await self.upsert_metric(
                product=product,
                namespace=namespace,
                metric_name=metric_name or alert.metric_name or "",
                metric_desc=None,  # 不覆盖用户编辑的描述
                unit=unit,
                dimensions=dimensions,
            )

            if metric.id:
                # 判断是新建还是更新（通过 flush 后的状态）
                stats["processed"] += 1

        # 去重统计
        unique_keys = len(seen_keys)
        stats["processed"] = unique_keys

        await self.db.commit()
        return stats

    async def sync_all(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        全量同步：从所有来源的告警中提取指标（分批查询避免内存风险）
        """
        total_stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0}
        offset = 0

        while True:
            conditions = [
                text("raw_data IS NOT NULL AND raw_data != 'null'::jsonb AND raw_data != '{}'::jsonb"),
                Alert.namespace.isnot(None),
            ]

            result = await self.db.execute(
                select(Alert)
                .where(and_(*conditions))
                .order_by(Alert.id.desc())
                .limit(batch_size)
                .offset(offset)
            )
            alerts = result.scalars().all()

            if not alerts:
                break

            seen_keys = set()
            for alert in alerts:
                namespace, metric_name, unit, dimensions = extract_namespace_metric(alert.raw_data, alert.source)

                if not namespace and not metric_name:
                    total_stats["skipped"] += 1
                    continue

                if not namespace:
                    namespace = alert.namespace or ""

                key = f"{alert.source}:{namespace}:{metric_name}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                product = get_product_name(alert.source, namespace)
                await self.upsert_metric(
                    product=product,
                    namespace=namespace,
                    metric_name=metric_name or alert.metric_name or "",
                    metric_desc=None,
                    unit=unit,
                    dimensions=dimensions,
                )

            total_stats["processed"] += len(seen_keys)
            offset += batch_size

        await self.db.commit()
        return total_stats
