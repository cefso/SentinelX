"""
SentinelX - 审计日志中间件
自动记录关键操作的审计日志
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json

from apps.core.logging import get_logger

log = get_logger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    审计日志中间件
    自动记录敏感操作的审计日志
    """

    # 需要记录审计日志的操作
    AUDIT_ACTIONS = {
        "POST": {
            "/api/v1/auth/login": "login",
            "/api/v1/auth/logout": "logout",
            "/api/v1/users": "user_create",
            "/api/v1/rules": "rule_create",
            "/api/v1/channels": "channel_create",
            "/api/v1/alerts": "alert_create",
        },
        "PUT": {
            "/api/v1/users": "user_update",
            "/api/v1/rules": "rule_update",
            "/api/v1/channels": "channel_update",
        },
        "DELETE": {
            "/api/v1/users": "user_delete",
            "/api/v1/rules": "rule_delete",
            "/api/v1/channels": "channel_delete",
        },
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取请求路径
        path = request.url.path

        # 查找匹配的审计操作
        method = request.method
        audit_action = None

        for prefix, actions in self.AUDIT_ACTIONS.items():
            if method == prefix:
                for action_path, action in actions.items():
                    if path.startswith(action_path):
                        audit_action = action
                        break

        # 执行请求
        response = await call_next(request)

        # 记录审计日志
        if audit_action and response.status_code < 400:
            # 从请求状态中获取用户信息
            user_id = getattr(request.state, "user_id", None)
            tenant_id = getattr(request.state, "tenant_id", None)
            username = getattr(request.state, "username", None)

            if user_id:
                log.info(
                    "audit_log",
                    action=audit_action,
                    method=method,
                    path=path,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    username=username,
                    status_code=response.status_code,
                )

        return response
