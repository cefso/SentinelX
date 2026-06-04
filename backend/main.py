"""
SentinelX - 综合告警平台
FastAPI 应用入口
"""
import logging

def _suppress_pgmq_logging():
    """Suppress noisy pgmq logger output."""
    for _name in ["pgmq.async_queue", "pgmq.decorators", "pgmq.logger"]:
        _log = logging.getLogger(_name)
        _log.setLevel(logging.WARNING)
        _log.propagate = False
        _log.handlers.clear()


_suppress_pgmq_logging()

# 配置 loguru（pgmq 使用），移除默认 handler 并设置级别
try:
    from loguru import logger as loguru_logger
    loguru_logger.remove()  # 移除默认的 stderr handler
except ImportError:
    pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from apps.core.config import settings
from apps.core.database import init_db, close_db
from apps.core.redis import RedisClient
from apps.core.logging import get_logger
from apps.core.middleware import (
    RequestLoggingMiddleware,
    PerformanceLoggingMiddleware,
    TenantContextMiddleware,
    ErrorHandlingMiddleware,
)
from apps.core.middleware_audit import AuditLoggingMiddleware
from apps.core.exceptions import SentinelXException, http_exception_from_sentinelx
from sqlalchemy import text

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import asyncio

    # 启动时
    logger.info("sentinelx_starting", version=settings.APP_VERSION)

    # 检查 JWT_SECRET_KEY 是否仍为默认值
    if settings.JWT_SECRET_KEY == "your-secret-key-change-in-production":
        logger.warning(
            "jwt_secret_key_is_default",
            message="JWT_SECRET_KEY is using the default value. "
                    "This is insecure in production. Set a unique secret in .env",
        )

    # 初始化数据库
    await init_db()
    logger.info("database_initialized")

    # 初始化Redis
    await RedisClient.get_instance()
    logger.info("redis_initialized")

    # 创建默认租户和超级管理员
    from apps.core.seed import seed_default_data
    await seed_default_data()

    # 启动告警升级Worker
    from apps.alert.services.escalation import EscalationWorker
    # 确保 pgmq 日志级别已设置（uvicorn 可能重新初始化 logging）
    _suppress_pgmq_logging()
    escalation_worker = EscalationWorker(check_interval_seconds=60)
    escalation_task = asyncio.create_task(escalation_worker.run())
    logger.info("escalation_worker_started")

    # 启动通知Worker
    from apps.notify.worker import NotificationWorker
    notification_worker = NotificationWorker()
    notification_task = asyncio.create_task(notification_worker.start())
    logger.info("notification_worker_started")

    # 启动告警消费 Consumer
    from apps.alert.services.dispatcher import AlertDispatcher
    from apps.core.mq import get_mq_async
    alert_consumer_task = asyncio.create_task(
        AlertDispatcher.start_consumer(await get_mq_async())
    )
    logger.info("alert_consumer_started")

    # 启动 AI 异步任务 Worker
    from apps.ai.worker import AIWorker
    ai_worker = AIWorker()
    ai_worker_task = asyncio.create_task(ai_worker.start())
    logger.info("ai_worker_started")

    yield

    # 关闭时
    logger.info("sentinelx_shutting_down")
    alert_consumer_task.cancel()
    escalation_task.cancel()
    await ai_worker.stop()
    ai_worker_task.cancel()
    await notification_worker.stop()
    notification_task.cancel()
    await RedisClient.close()
    await close_db()
    logger.info("sentinelx_stopped")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="企业级综合告警平台 - 多租户、高可用、智能路由",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义中间件
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PerformanceLoggingMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(AuditLoggingMiddleware)


# 异常处理器
@app.exception_handler(SentinelXException)
async def sentinelx_exception_handler(request: Request, exc: SentinelXException):
    """SentinelX自定义异常处理"""
    http_exc = http_exception_from_sentinelx(exc)
    logger.error(
        "sentinelx_exception",
        code=exc.code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理"""
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation error",
            "code": "VALIDATION_ERROR",
            "details": {"errors": exc.errors()},
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal server error",
            "code": "INTERNAL_ERROR",
            "details": {},
        }
    )


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
    }


@app.get("/health/ready")
async def readiness_check():
    """
    就绪探针 - 检查所有依赖服务
    Kubernetes会使用此端点判断容器是否就绪
    """
    checks = {
        "database": "unknown",
        "redis": "unknown",
    }
    is_ready = True

    # 检查数据库
    try:
        from apps.core.database import async_engine
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:50]}"
        is_ready = False

    # 检查Redis
    try:
        from apps.core.redis import RedisClient
        redis = await RedisClient.get_instance()
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)[:50]}"
        is_ready = False

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
    }


@app.get("/health/live")
async def liveness_check():
    """
    存活探针 - 检查应用进程是否存活
    Kubernetes会使用此端点判断容器是否需要重启
    """
    return {"status": "alive"}


@app.get("/health/build")
async def build_info():
    """
    构建信息接口 - 返回版本和 git commit 信息
    """
    return {
        "version": settings.APP_VERSION,
        "git_commit": settings.GIT_COMMIT,
        "build_id": settings.BUILD_ID,
        "build_time": settings.BUILD_TIME,
    }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


# 导入并注册路由
from apps.auth.routers import router as auth_router
from apps.tenant.routers import router as tenant_router
from apps.alert.routers import router as alert_router
from apps.rule.routers import router as rule_router
from apps.notify.routers import router as notify_router
from apps.ai.routers import router as ai_router
from apps.callback.router import router as callback_router
from apps.escalation.router import router as escalation_router
from apps.maintenance.router import router as maintenance_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["认证"])
app.include_router(tenant_router, prefix=settings.API_V1_PREFIX, tags=["租户管理"])
app.include_router(alert_router, prefix=settings.API_V1_PREFIX, tags=["告警"])
app.include_router(escalation_router, prefix=settings.API_V1_PREFIX, tags=["告警升级"])
app.include_router(maintenance_router, prefix=settings.API_V1_PREFIX, tags=["维护窗口"])
app.include_router(rule_router, prefix=settings.API_V1_PREFIX, tags=["规则"])
app.include_router(notify_router, prefix=settings.API_V1_PREFIX, tags=["通知"])
app.include_router(ai_router, prefix=settings.API_V1_PREFIX, tags=["AI"])
app.include_router(callback_router, prefix=settings.API_V1_PREFIX, tags=["回调"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="info",
    )
