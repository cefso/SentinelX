"""
SentinelX - 自定义异常类
"""
from typing import Optional, Any
from fastapi import HTTPException, status


class SentinelXException(Exception):
    """SentinelX基础异常"""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.message = message
        self.code = code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(SentinelXException):
    """认证错误"""

    def __init__(self, message: str = "Authentication failed", details: Optional[dict] = None):
        super().__init__(message, code="AUTH_ERROR", details=details)


class AuthorizationError(SentinelXException):
    """授权错误"""

    def __init__(self, message: str = "Permission denied", details: Optional[dict] = None):
        super().__init__(message, code="AUTHZ_ERROR", details=details)


class ResourceNotFoundError(SentinelXException):
    """资源不存在"""

    def __init__(self, resource: str, resource_id: Any):
        message = f"{resource} with id '{resource_id}' not found"
        super().__init__(message, code="NOT_FOUND", details={"resource": resource, "id": resource_id})


class DuplicateResourceError(SentinelXException):
    """资源重复"""

    def __init__(self, resource: str, identifier: str):
        message = f"{resource} with identifier '{identifier}' already exists"
        super().__init__(message, code="DUPLICATE", details={"resource": resource, "identifier": identifier})


class ValidationError(SentinelXException):
    """验证错误"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field})


class QuotaExceededError(SentinelXException):
    """配额超限"""

    def __init__(self, quota_type: str, limit: int):
        message = f"{quota_type} quota exceeded. Limit: {limit}"
        super().__init__(message, code="QUOTA_EXCEEDED", details={"quota_type": quota_type, "limit": limit})


class TenantNotFoundError(ResourceNotFoundError):
    """租户不存在"""

    def __init__(self, tenant_id: str):
        super().__init__("Tenant", tenant_id)


class AlertNotFoundError(ResourceNotFoundError):
    """告警不存在"""

    def __init__(self, alert_id: str):
        super().__init__("Alert", alert_id)


class RuleNotFoundError(ResourceNotFoundError):
    """规则不存在"""

    def __init__(self, rule_id: str):
        super().__init__("Rule", rule_id)


class ChannelNotFoundError(ResourceNotFoundError):
    """通知渠道不存在"""

    def __init__(self, channel_id: str):
        super().__init__("Channel", channel_id)


class ExternalServiceError(SentinelXException):
    """外部服务错误"""

    def __init__(self, service: str, message: str):
        super().__init__(
            f"External service error: {service}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, "message": message}
        )


class RateLimitError(SentinelXException):
    """限流错误"""

    def __init__(self, retry_after: int = 60):
        message = f"Rate limit exceeded. Retry after {retry_after} seconds"
        super().__init__(message, code="RATE_LIMIT", details={"retry_after": retry_after})


def http_exception_from_sentinelx(exc: SentinelXException) -> HTTPException:
    """将SentinelX异常转换为FastAPI HTTPException"""
    status_map = {
        "AUTH_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHZ_ERROR": status.HTTP_403_FORBIDDEN,
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "DUPLICATE": status.HTTP_409_CONFLICT,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "QUOTA_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
        "RATE_LIMIT": status.HTTP_429_TOO_MANY_REQUESTS,
    }

    status_code = status_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return HTTPException(
        status_code=status_code,
        detail={
            "message": exc.message,
            "code": exc.code,
            "details": exc.details,
        }
    )
