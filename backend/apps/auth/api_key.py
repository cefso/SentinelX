"""
SentinelX - API Key认证
用于Agent和服务间的高效认证
"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.core.security import encryptor
from apps.core.exceptions import AuthenticationError
from apps.tenant.models import Tenant

logger = structlog.get_logger(__name__)


class APIKeyAuth:
    """
    API Key认证服务
    用于Agent和内部服务认证
    """

    # API Key格式: {prefix}_{key_id}_{secret_key}
    # 示例: sxk_prod_abc123def456

    PREFIX = "sxk"
    VERSION = "v1"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_api_key(
        self,
        tenant_id: int,
        name: str,
        expires_days: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        创建API Key
        返回: (api_key, secret_key) - secret_key只显示一次
        """
        # 生成Key ID (8字节随机)
        key_id = secrets.token_hex(8)

        # 生成Secret Key (32字节随机)
        secret_key = secrets.token_hex(32)

        # 计算签名用于验证
        signature = self._calculate_signature(key_id, secret_key)

        # 加密存储
        encrypted_secret = encryptor.encrypt(secret_key)

        # 构建API Key
        api_key = f"{self.PREFIX}_{self.VERSION}_{key_id}"

        # 更新租户的API Token
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise AuthenticationError("Tenant not found")

        # 存储加密的密钥
        if not tenant.api_token:
            tenant.api_token = "{}"
        import json
        tokens = json.loads(tenant.api_token)
        tokens[key_id] = {
            "name": name,
            "secret_signature": signature,
            "encrypted_secret": encrypted_secret,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=expires_days)).isoformat() if expires_days else None,
            "is_active": True,
        }
        tenant.api_token = json.dumps(tokens)
        await self.db.commit()

        logger.info("api_key_created", tenant_id=tenant_id, key_id=key_id, name=name)

        # 返回完整的API Key (包含secret)
        full_api_key = f"{api_key}_{secret_key}"
        return api_key, full_api_key

    async def verify_api_key(self, api_key: str) -> Optional[Tenant]:
        """
        验证API Key
        返回: Tenant对象或None
        """
        try:
            # 解析API Key
            parts = api_key.split("_")
            if len(parts) != 4:
                return None

            prefix, version, key_id, secret_key = parts

            if prefix != self.PREFIX or version != self.VERSION:
                return None

            # 查询租户
            result = await self.db.execute(select(Tenant))
            tenants = result.scalars().all()

            for tenant in tenants:
                if not tenant.api_token:
                    continue

                import json
                try:
                    tokens = json.loads(tenant.api_token)
                except json.JSONDecodeError:
                    continue

                token_info = tokens.get(key_id)
                if not token_info:
                    continue

                # 检查是否激活
                if not token_info.get("is_active", False):
                    logger.warning("api_key_inactive", tenant_id=tenant.id, key_id=key_id)
                    return None

                # 检查是否过期
                expires_at = token_info.get("expires_at")
                if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
                    logger.warning("api_key_expired", tenant_id=tenant.id, key_id=key_id)
                    return None

                # 验证签名
                expected_signature = token_info.get("secret_signature")
                actual_signature = self._calculate_signature(key_id, secret_key)

                if not hmac.compare_digest(expected_signature, actual_signature):
                    logger.warning("api_key_signature_mismatch", tenant_id=tenant.id, key_id=key_id)
                    return None

                logger.info("api_key_verified", tenant_id=tenant.id, key_id=key_id)
                return tenant

            return None

        except Exception as e:
            logger.error("api_key_verification_error", error=str(e))
            return None

    async def revoke_api_key(self, tenant_id: int, key_id: str) -> bool:
        """撤销API Key"""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.api_token:
            return False

        import json
        tokens = json.loads(tenant.api_token)
        if key_id not in tokens:
            return False

        tokens[key_id]["is_active"] = False
        tenant.api_token = json.dumps(tokens)
        await self.db.commit()

        logger.info("api_key_revoked", tenant_id=tenant_id, key_id=key_id)
        return True

    async def list_api_keys(self, tenant_id: int) -> list:
        """列出API Key (不包含secret)"""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.api_token:
            return []

        import json
        try:
            tokens = json.loads(tenant.api_token)
        except json.JSONDecodeError:
            return []

        keys = []
        for key_id, info in tokens.items():
            keys.append({
                "key_id": key_id,
                "name": info.get("name"),
                "created_at": info.get("created_at"),
                "expires_at": info.get("expires_at"),
                "is_active": info.get("is_active", False),
            })
        return keys

    def _calculate_signature(self, key_id: str, secret_key: str) -> str:
        """计算签名"""
        message = f"{self.PREFIX}:{self.VERSION}:{key_id}"
        return hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
