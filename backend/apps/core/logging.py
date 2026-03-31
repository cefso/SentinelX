"""
SentinelX - 日志配置
使用 structlog 进行结构化日志记录
"""
import sys
import structlog
from structlog.types import EventDict, WrappedLogger
from typing import Any, Dict
from datetime import datetime


def _is_debug() -> bool:
    """检查是否为调试模式"""
    import os
    return os.getenv("DEBUG", "false").lower() == "true"


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
        structlog.processors.JSONRenderer() if not _is_debug() else _console_renderer,
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
