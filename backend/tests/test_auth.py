"""
SentinelX - 认证服务测试
"""
import pytest
from apps.auth.services.auth import PermissionService, AuditService
from apps.auth.api_key import APIKeyAuth


def test_permission_service_builtin_permissions():
    """测试内置权限定义"""
    assert "alerts:read" in PermissionService.PERMISSIONS
    assert "alerts:write" in PermissionService.PERMISSIONS
    assert "admin" in PermissionService.PERMISSIONS


def test_permission_labels():
    """测试权限标签"""
    assert PermissionService.PERMISSIONS["alerts:read"] == "查看告警"
    assert PermissionService.PERMISSIONS["admin"] == "管理员(全部权限)"


class TestAPIKeyFormat:
    """测试API Key格式"""

    def test_api_key_format(self):
        """测试API Key格式"""
        api_key_auth = APIKeyAuth(None)

        # API Key格式: sxk_v1_{key_id} (3部分)
        # 完整格式(含secret，用于首次创建时显示): sxk_v1_{key_id}_{secret_key}
        key = "sxk_v1_abc123def456ab12"
        parts = key.split("_")

        assert len(parts) == 3
        assert parts[0] == "sxk"
        assert parts[1] == "v1"
        assert len(parts[2]) == 16  # key_id (8字节hex = 16字符)

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
