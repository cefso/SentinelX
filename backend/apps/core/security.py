"""
SentinelX - 安全相关工具
JWT认证、密码加密、AES加密等
"""
import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from apps.core.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建JWT刷新令牌"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """验证令牌"""
    payload = decode_token(token)
    if payload and payload.get("type") == token_type:
        return payload
    return None


# AES加密 (用于敏感配置存储)
class AESEncryptor:
    """AES加密工具"""

    def __init__(self, key: Optional[str] = None):
        # 使用配置的密钥或生成默认密钥（仅用于开发，生产应使用环境变量）
        self.key = key or settings.JWT_SECRET_KEY
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """创建Fernet实例"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.key.encode()[:16].ljust(16, b'0'),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.key.encode()[:32].ljust(32, b'0')))
        return Fernet(key)

    def encrypt(self, data: str) -> str:
        """加密字符串"""
        encrypted = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密字符串"""
        data = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self._fernet.decrypt(data)
        return decrypted.decode()


# API签名验证
def generate_signature(secret: str, timestamp: str, body: str = "") -> str:
    """生成API签名"""
    message = f"{timestamp}{body}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_signature(secret: str, timestamp: str, body: str, signature: str) -> bool:
    """验证API签名"""
    expected = generate_signature(secret, timestamp, body)
    return hmac.compare_digest(expected, signature)


# 全局加密器实例
encryptor = AESEncryptor()
