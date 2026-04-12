"""
SentinelX - 维护窗口服务
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.maintenance.model import MaintenanceWindow
from apps.alert.models import Alert

logger = structlog.get_logger()


class MaintenanceService:
    """维护窗口服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_window(
        self,
        tenant_id: str,
        name: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> MaintenanceWindow:
        """创建维护窗口"""
        window = MaintenanceWindow(
            tenant_id=tenant_id,
            name=name,
            description=description,
            start_time=start_time,
            end_time=end_time,
            scope=scope or {},
            is_active=True,
        )
        self.db.add(window)
        await self.db.commit()
        await self.db.refresh(window)

        # 同步到 Redis
        await self._sync_to_redis(window)

        logger.info(
            "maintenance_window_created",
            window_id=window.id,
            tenant_id=tenant_id,
            name=name,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
        )
        return window

    async def list_windows(
        self,
        tenant_id: str,
        active_only: bool = False,
    ) -> List[MaintenanceWindow]:
        """列出维护窗口"""
        query = select(MaintenanceWindow).where(MaintenanceWindow.tenant_id == tenant_id)
        if active_only:
            now = datetime.now(timezone.utc)
            query = query.where(
                and_(
                    MaintenanceWindow.is_active == True,
                    MaintenanceWindow.start_time <= now,
                    MaintenanceWindow.end_time >= now,
                )
            )
        result = await self.db.execute(query.order_by(MaintenanceWindow.start_time.desc()))
        return list(result.scalars().all())

    async def get_window(self, window_id: int, tenant_id: str) -> Optional[MaintenanceWindow]:
        """获取维护窗口"""
        result = await self.db.execute(
            select(MaintenanceWindow).where(
                MaintenanceWindow.id == window_id,
                MaintenanceWindow.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_window(
        self,
        window_id: int,
        tenant_id: str,
        **kwargs,
    ) -> Optional[MaintenanceWindow]:
        """更新维护窗口"""
        window = await self.get_window(window_id, tenant_id)
        if not window:
            return None

        for field, value in kwargs.items():
            if hasattr(window, field):
                setattr(window, field, value)

        await self.db.commit()
        await self.db.refresh(window)

        # 同步到 Redis
        await self._sync_to_redis(window)

        logger.info("maintenance_window_updated", window_id=window_id, tenant_id=tenant_id)
        return window

    async def delete_window(self, window_id: int, tenant_id: str) -> bool:
        """删除维护窗口"""
        window = await self.get_window(window_id, tenant_id)
        if not window:
            return False

        await self.db.delete(window)
        await self.db.commit()

        # 从 Redis 删除
        from apps.core.redis import RedisClient
        redis = await RedisClient.get_instance()
        await redis.hdel(f"suppress:{tenant_id}", f"window:{window_id}")

        logger.info("maintenance_window_deleted", window_id=window_id, tenant_id=tenant_id)
        return True

    async def is_alert_suppressed(
        self,
        tenant_id: str,
        alert: Alert,
    ) -> tuple[bool, Optional[str]]:
        """
        检查告警是否应该被抑制
        返回: (是否抑制, 抑制原因)
        """
        now = datetime.now(timezone.utc)

        # 查询当前有效的维护窗口
        result = await self.db.execute(
            select(MaintenanceWindow).where(
                MaintenanceWindow.tenant_id == tenant_id,
                MaintenanceWindow.is_active == True,
                MaintenanceWindow.start_time <= now,
                MaintenanceWindow.end_time >= now,
            )
        )
        windows = result.scalars().all()

        for window in windows:
            if self._matches_scope(alert, window.scope):
                return True, f"维护窗口: {window.name} (ID: {window.id})"

        return False, None

    def _matches_scope(self, alert: Alert, scope: Dict[str, Any]) -> bool:
        """检查告警是否匹配维护窗口范围"""
        if not scope:
            return True  # 空范围表示全部匹配

        # 按 labels 过滤
        if "labels" in scope:
            alert_labels = alert.labels or {}
            for key, value in scope["labels"].items():
                if alert_labels.get(key) != value:
                    return False

        # 按 severity 过滤
        if "severity" in scope:
            if alert.severity not in scope["severity"]:
                return False

        # 按 source 过滤
        if "source" in scope:
            if alert.source not in scope["source"]:
                return False

        return True

    async def _sync_to_redis(self, window: MaintenanceWindow):
        """同步维护窗口到 Redis"""
        from apps.core.redis import RedisClient

        redis = await RedisClient.get_instance()
        key = f"suppress:{window.tenant_id}"
        field = f"window:{window.id}"

        scope_data = window.scope or {}
        await redis.hset(key, field, str(scope_data))

        # 设置过期时间
        ttl = int((window.end_time - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            await redis.expire(key, ttl + 3600)  # 多加1小时缓冲
        else:
            await redis.hdel(key, field)

    async def check_and_suppress(self, tenant_id: str) -> Dict[str, Any]:
        """检查并返回当前活跃的维护窗口"""
        windows = await self.list_windows(tenant_id, active_only=True)
        return {
            "active_count": len(windows),
            "windows": [
                {
                    "id": w.id,
                    "name": w.name,
                    "start_time": w.start_time.isoformat(),
                    "end_time": w.end_time.isoformat(),
                    "scope": w.scope,
                }
                for w in windows
            ],
        }
