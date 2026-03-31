"""
SentinelX - 综合告警平台
FastAPI 应用入口
"""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from apps.core.config import settings
from apps.core.database import init_db, close_db
from apps.core.redis import RedisClient
from apps.core.exceptions import SentinelXException, http_exception_from_sentinelx

# 配置structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


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

app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["认证"])
app.include_router(tenant_router, prefix=settings.API_V1_PREFIX, tags=["租户管理"])
app.include_router(alert_router, prefix=settings.API_V1_PREFIX, tags=["告警"])
app.include_router(rule_router, prefix=settings.API_V1_PREFIX, tags=["规则"])
app.include_router(notify_router, prefix=settings.API_V1_PREFIX, tags=["通知"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
