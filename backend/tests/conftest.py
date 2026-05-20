"""
SentinelX - 测试配置
"""
import pytest
import asyncio
from typing import AsyncGenerator

# 设置测试环境变量
import os
from pathlib import Path

_env_test = Path(__file__).resolve().parent.parent / ".env.test"
if _env_test.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_test)
    except ImportError:
        pass

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "sentinelx_test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator:
    """数据库会话fixture"""
    from apps.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def redis_client():
    """Redis客户端fixture"""
    from apps.core.redis import RedisClient

    client = await RedisClient.get_instance()
    yield client
    await RedisClient.close()
