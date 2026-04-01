"""
SentinelX - 综合告警平台
FastAPI 应用入口
"""
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
from apps.core.exceptions import SentinelXException

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("sentinelx_starting", version=settings.APP_VERSION)

    # 初始化数据库
    await init_db()
    logger.info("database_initialized")

    # 初始化Redis
    await RedisClient.get_instance()
    logger.info("redis_initialized")

    # 创建默认租户和超级管理员
    from apps.core.seed import seed_default_data
    await seed_default_data()

    yield

    # 关闭时
    logger.info("sentinelx_shutting_down")
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
    logger.error(
        "sentinelx_exception",
        code=exc.code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "message": exc.message,
            "code": exc.code,
            "details": exc.details,
        }
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

app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["认证"])
app.include_router(tenant_router, prefix=settings.API_V1_PREFIX, tags=["租户管理"])
app.include_router(alert_router, prefix=settings.API_V1_PREFIX, tags=["告警"])
app.include_router(rule_router, prefix=settings.API_V1_PREFIX, tags=["规则"])
app.include_router(notify_router, prefix=settings.API_V1_PREFIX, tags=["通知"])
app.include_router(ai_router, prefix=settings.API_V1_PREFIX, tags=["AI"])
app.include_router(callback_router, prefix=settings.API_V1_PREFIX, tags=["回调"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
