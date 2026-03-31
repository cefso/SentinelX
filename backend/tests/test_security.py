"""
SentinelX - 安全工具测试
"""
import pytest
from apps.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    generate_signature,
    verify_signature,
    encryptor,
)


def test_password_hash_and_verify():
    """测试密码哈希和验证"""
    password = "test_password_123"

    hashed = hash_password(password)
    assert hashed != password
    assert len(hashed) > 0

    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_access_token():
    """测试JWT访问令牌"""
    data = {"sub": 1, "tenant_id": 1, "username": "test"}

    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0

    payload = verify_token(token, "access")
    assert payload is not None
    assert payload["sub"] == 1
    assert payload["tenant_id"] == 1


def test_verify_token_wrong_type():
    """测试验证错误类型的令牌"""
    data = {"sub": 1, "tenant_id": 1}
    token = create_access_token(data)

    # 使用refresh类型验证access令牌应该失败
    result = verify_token(token, "refresh")
    assert result is None


def test_signature():
    """测试API签名"""
    secret = "test_secret"
    timestamp = "1234567890"
    body = '{"key": "value"}'

    signature = generate_signature(secret, timestamp, body)
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex

    assert verify_signature(secret, timestamp, body, signature) is True
    assert verify_signature(secret, timestamp, body, "wrong") is False


def test_aes_encryptor():
    """测试AES加密"""
    original = "sensitive_data_123"

    encrypted = encryptor.encrypt(original)
    assert encrypted != original

    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == original
