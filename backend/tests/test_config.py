"""
SentinelX - 配置测试
"""
import pytest
from apps.core.config import Settings, get_settings


def test_settings_defaults():
    """测试默认配置"""
    settings = Settings()

    assert settings.APP_NAME == "SentinelX"
    assert settings.APP_VERSION == "1.0.0"
    assert settings.DEBUG is False
    assert settings.DB_PORT == 5432
    assert settings.REDIS_PORT == 6379


def test_settings_database_url():
    """测试数据库URL构建"""
    settings = Settings(
        DB_HOST="localhost",
        DB_PORT=5432,
        DB_USER="test",
        DB_PASSWORD="test123",
        DB_NAME="testdb"
    )

    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert "test:test123" in settings.DATABASE_URL
    assert "localhost:5432" in settings.DATABASE_URL
    assert "testdb" in settings.DATABASE_URL


def test_settings_redis_url():
    """测试Redis URL构建"""
    settings = Settings(
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=0
    )

    assert "redis://localhost:6379/0" in settings.REDIS_URL


def test_settings_redis_url_with_password():
    """测试带密码的Redis URL构建"""
    settings = Settings(
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_PASSWORD="secret",
        REDIS_DB=1
    )

    assert "redis://:secret@localhost:6379/1" in settings.REDIS_URL


def test_get_settings_cached():
    """测试配置单例"""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
