"""
SentinelX - 数据库连接管理
支持 PostgreSQL + TimescaleDB
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apps.core.config import settings

# 异步引擎 (主数据库操作)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# 异步Session工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 同步引擎 (用于Alembic迁移等)
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
)

# 声明基类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖注入"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """上下文管理器方式的数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库 (创建扩展、超表等)"""
    from sqlalchemy import text

    async with async_engine.begin() as conn:
        # 创建TimescaleDB扩展
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))

        # 创建UUID扩展
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))


async def close_db():
    """关闭数据库连接"""
    await async_engine.dispose()
