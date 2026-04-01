"""
SentinelX - 中间件
请求日志、性能追踪、错误处理等
"""
import time
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from apps.core.logging import get_logger
from apps.core.utils import get_client_ip

log = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    记录所有请求的路径、方法、响应状态和耗时
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始
        request_id = request.headers.get("X-Request-ID", _generate_request_id())
        start_time = time.time()

        # 构建请求日志
        log.info(
            "request_started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )

        # 添加 request_id 到请求状态
        request.state.request_id = request_id

        try:
            response = await call_next(request)

            # 计算耗时
            duration = time.time() - start_time

            # 记录请求完成
            log.info(
                "request_completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # 在响应头中添加 request_id
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # 计算耗时
            duration = time.time() - start_time

            # 记录错误
            log.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error_type=type(exc).__name__,
                error_message=str(exc),
                duration_ms=round(duration * 1000, 2),
                traceback=traceback.format_exc(),
            )

            raise


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    性能日志中间件
    记录慢请求（超过阈值）
    """

    SLOW_REQUEST_THRESHOLD_MS = 1000  # 1秒

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # 如果请求超过阈值，记录警告
        if duration * 1000 > self.SLOW_REQUEST_THRESHOLD_MS:
            log.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                threshold_ms=self.SLOW_REQUEST_THRESHOLD_MS,
            )

        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    租户上下文中间件
    从请求中提取租户信息并添加到请求状态
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 从路径参数、查询参数或header中提取租户ID
        tenant_id = (
            request.path_params.get("tenant_id")
            or request.query_params.get("tenant_id")
            or request.headers.get("X-Tenant-ID")
        )

        request.state.tenant_id = tenant_id

        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    统一错误处理中间件
    将未处理的异常转换为标准JSON响应
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            log.error(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

            return JSONResponse(
                status_code=500,
                content={
                    "message": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "details": {},
                }
            )


def _generate_request_id() -> str:
    """生成请求ID"""
    import uuid
    return str(uuid.uuid4())[:8]
