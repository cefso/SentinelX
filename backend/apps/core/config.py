"""
SentinelX - 综合告警平台配置管理
"""
import json
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


def _load_build_info() -> dict:
    """从版本文件加载构建信息"""
    try:
        path = Path(__file__).parent.parent.parent / "build-info.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {"git_commit": "unknown", "build_id": "unknown", "build_time": ""}


BUILD_INFO = _load_build_info()


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "SentinelX"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # 构建信息
    GIT_COMMIT: str = BUILD_INFO.get("git_commit", "unknown")
    BUILD_ID: str = BUILD_INFO.get("build_id", "unknown")
    BUILD_TIME: str = BUILD_INFO.get("build_time", "")

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "sentinelx"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 20

    # JWT配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI配置
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DASHSCOPE_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-4o"
    AI_PROVIDER: str = "openai"

    # 配额默认配置
    DEFAULT_MAX_ALERTS: int = 10000
    DEFAULT_MAX_USERS: int = 10
    DEFAULT_MAX_RULES: int = 100
    DEFAULT_MAX_CHANNELS: int = 20

    # PGMQ配置
    PGMQ_ENABLED: bool = True

    # 日志配置
    LOG_LEVEL: str = "INFO"  # DEBUG/INFO/WARNING/ERROR
    LOG_FORMAT: str = "json"  # json/console
    LOG_FILE: Optional[str] = None  # 日志文件路径
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
