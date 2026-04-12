"""
SentinelX - 消息队列管理
支持 PGMQ (PostgreSQL原生消息队列)
"""
import json
from typing import Optional, Any, List, Dict
from datetime import datetime
from urllib.parse import urlparse
from apps.core.config import settings

# PGMQ导入 (可选)
try:
    import pgmq
    from pgmq.async_queue import PGMQueue

    PGMQ_AVAILABLE = True
except ImportError:
    PGMQ_AVAILABLE = False
    PGMQueue = None


class MessageQueue:
    """
    PGMQ - PostgreSQL原生消息队列
    - 无需独立MQ服务
    - 消息持久化依托PG事务
    - 支持延迟队列、死信队列、消费确认
    """

    def __init__(self, database_url: str):
        if not PGMQ_AVAILABLE:
            raise ImportError("pgmq not installed. Run: pip install pgmq")
        # 解析 postgresql://user:pass@host:port/dbname
        parsed = urlparse(database_url)
        self.mq = PGMQueue(
            host=parsed.hostname or "localhost",
            port=str(parsed.port or 5432),
            database=parsed.path.lstrip("/") or "postgres",
            username=parsed.username or "postgres",
            password=parsed.password or "",
        )
        self._queues_initialized = False

    async def init_queues(self):
        """初始化队列"""
        if self._queues_initialized:
            return

        queues = ["alerts_raw", "alerts_notify", "alerts_dlq", "alerts_ai"]

        for queue_name in queues:
            try:
                await self.mq.create_queue(queue_name)
            except Exception:
                # 队列已存在
                pass

        self._queues_initialized = True

    async def send(self, queue: str, message: Dict[str, Any]) -> int:
        """发送消息，返回消息ID"""
        return await self.mq.send(queue, message)

    async def receive(self, queue: str, count: int = 1, vt: Optional[int] = None):
        """消费消息"""
        if count == 1:
            return await self.mq.read(queue, vt=vt)
        return await self.mq.read_batch(queue, vt=vt, batch_size=count)

    async def ack(self, queue: str, message_id: int):
        """确认消息已处理"""
        await self.mq.delete(queue, message_id)

    async def nack(self, queue: str, message_id: int, vt: int = 300):
        """未确认，延迟重试"""
        await self.mq.read(queue, vt=vt)

    async def purge(self, queue: str):
        """清空队列"""
        await self.mq.purge(queue)


# 全局MQ实例
_mq_instance: Optional[MessageQueue] = None


def get_mq() -> MessageQueue:
    """获取MQ实例"""
    global _mq_instance
    if _mq_instance is None:
        _mq_instance = MessageQueue(settings.SYNC_DATABASE_URL)
    return _mq_instance


async def get_mq_async() -> MessageQueue:
    """异步获取MQ实例"""
    mq = get_mq()
    if not mq._queues_initialized:
        await mq.init_queues()
    return mq
