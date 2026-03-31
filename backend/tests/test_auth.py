"""
SentinelX - 认证服务测试
"""
import pytest
from apps.auth.services.auth import PermissionService, AuditService
from apps.auth.api_key import APIKeyAuth


def test_permission_service_builtin_permissions():
    """测试内置权限定义"""
    assert "alert:read" in PermissionService.PERMISSIONS
    assert "alert:write" in PermissionService.PERMISSIONS
    assert "admin" in PermissionService.PERMISSIONS
    assert "read" in PermissionService.PERMISSIONS


def test_permission_labels():
    """测试权限标签"""
    assert PermissionService.PERMISSIONS["alert:read"] == "查看告警"
    assert PermissionService.PERMISSIONS["admin"] == "管理员(全部权限)"


class TestAPIKeyFormat:
    """测试API Key格式"""

    def test_api_key_format(self):
        """测试API Key格式"""
        api_key_auth = APIKeyAuth(None)

        # API Key应该包含: prefix_version_keyid_secret
        # 例如: sxk_v1_abc123def456_xxx
        key = "sxk_v1_abc123def456_xxx"
        parts = key.split("_")

        assert len(parts) == 4
        assert parts[0] == "sxk"
        assert parts[1] == "v1"
        assert len(parts[2]) == 16  # key_id (8字节hex)
        assert len(parts[3]) == 64  # secret_key (32字节hex)

    def test_api_key_prefix(self):
        """测试API Key前缀"""
        api_key_auth = APIKeyAuth(None)
        assert api_key_auth.PREFIX == "sxk"
        assert api_key_auth.VERSION == "v1"

    def test_calculate_signature(self):
        """测试签名计算"""
        api_key_auth = APIKeyAuth(None)

        key_id = "abc123def456"
        secret_key = "x" * 64

        signature = api_key_auth._calculate_signature(key_id, secret_key)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex
