"""
SentinelX - 日志配置
使用 structlog 进行结构化日志记录
"""
import sys
import os
import logging
from logging.handlers import RotatingFileHandler
import structlog
from structlog.types import EventDict, WrappedLogger
from typing import Any, Dict
from datetime import datetime

from apps.core.config import settings


def _get_log_level() -> int:
    """获取日志级别"""
    level = os.getenv("LOG_LEVEL", settings.LOG_LEVEL).upper()
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return levels.get(level, logging.INFO)


def _is_debug() -> bool:
    """检查是否为调试模式"""
    return settings.DEBUG or os.getenv("DEBUG", "false").lower() == "true"


def _add_service_context(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """添加服务上下文信息"""
    event_dict["service"] = "sentinelx"
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def _console_renderer(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> str:
    """控制台彩色输出"""
    level = method_name.upper()
    timestamp = event_dict.pop("timestamp", "")
    logger_name = event_dict.pop("logger", "")
    event = event_dict.pop("event", "")

    # 颜色
    colors = {
        "DEBUG": "\033[36m",    # 青色
        "INFO": "\033[32m",     # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",    # 红色
        "CRITICAL": "\033[35m", # 紫色
    }
    reset = "\033[0m"
    color = colors.get(level, "")

    # 构建输出
    parts = [f"{color}{timestamp}{reset}"]
    if logger_name:
        parts.append(f"[{logger_name}]")
    parts.append(f"{color}{level}{reset}: {event}")

    # 添加额外字段
    if event_dict:
        items = []
        for key, value in sorted(event_dict.items()):
            if isinstance(value, dict):
                items.append(f"  {key}={value}")
            else:
                items.append(f"  {key}={value}")
        if items:
            parts.append("\n" + "\n".join(items))

    return " ".join(parts)


def _configure_root_logger():
    """配置根日志器"""
    root_logger = logging.getLogger()
    root_logger.setLevel(_get_log_level())

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_get_log_level())

    if settings.LOG_FORMAT == "json" and not _is_debug():
        console_handler.setFormatter(logging.Formatter(
            '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
        ))
    else:
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    root_logger.addHandler(console_handler)

    # 文件处理器（如果配置）
    if settings.LOG_FILE:
        try:
            # 确保日志目录存在
            log_dir = os.path.dirname(settings.LOG_FILE)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=settings.LOG_MAX_BYTES,
                backupCount=settings.LOG_BACKUP_COUNT,
                encoding="utf-8"
            )
            file_handler.setLevel(_get_log_level())
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Failed to setup file logger: {e}")


# 初始化根日志器
_configure_root_logger()

# 配置 structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _add_service_context,
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" and not _is_debug() else _console_renderer,
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    获取日志记录器

    用法:
        log = get_logger(__name__)
        log.info("message", key="value")
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


class LoggerMixin:
    """日志混入类，为类添加日志功能"""

    @property
    def log(self) -> structlog.stdlib.BoundLogger:
        if not hasattr(self, "_logger"):
            self._logger = structlog.get_logger(self.__class__.__name__)
        return self._logger
