"""
SentinelX - Redis连接管理
"""
import asyncio
import redis.asyncio as redis
from typing import Optional
import structlog
from apps.core.config import settings

logger = structlog.get_logger()


class RedisClient:
    """Redis异步客户端单例"""

    _instance: Optional[redis.Redis] = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    try:
                        cls._instance = redis.Redis(
                            host=settings.REDIS_HOST,
                            port=settings.REDIS_PORT,
                            password=settings.REDIS_PASSWORD,
                            db=settings.REDIS_DB,
                            decode_responses=True,
                            max_connections=settings.REDIS_POOL_SIZE,
                        )
                        # 验证连接
                        await cls._instance.ping()
                        logger.info("redis_connected", host=settings.REDIS_HOST, port=settings.REDIS_PORT)
                    except Exception as e:
                        logger.warning("redis_connection_failed", host=settings.REDIS_HOST, port=settings.REDIS_PORT, error=str(e))
                        raise
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


async def get_redis() -> redis.Redis:
    """获取Redis连接的依赖注入"""
    return await RedisClient.get_instance()
