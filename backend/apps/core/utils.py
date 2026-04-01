"""
SentinelX - 公共工具函数
"""
from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实IP

    优先级:
    1. X-Forwarded-For (负载均衡/代理场景)
    2. X-Real-IP (Nginx 代理场景)
    3. request.client.host (直接访问场景)
    """
    # 优先从 X-Forwarded-For 获取
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # 其次从 X-Real-IP 获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 最后从 client_host 获取
    if request.client:
        return request.client.host

    return "unknown"
