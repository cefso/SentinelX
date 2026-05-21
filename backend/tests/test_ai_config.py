"""
SentinelX - AI 配置与提供商测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from apps.core.security import encryptor
from apps.ai.config import decrypt_api_key, resolve_api_key_for_list
from apps.ai.providers import resolve_base_url
from apps.ai.client import ProviderRegistry, _filter_openai_models, OpenAICompatibleClient
from fastapi import HTTPException


def test_resolve_base_url_presets():
    assert resolve_base_url("openai", None) == "https://api.openai.com/v1"
    assert resolve_base_url("deepseek", None) == "https://api.deepseek.com/v1"
    assert resolve_base_url("openai", "https://custom.example/v1") == "https://custom.example/v1"


def test_resolve_base_url_custom():
    assert resolve_base_url("custom", None) == ""
    assert resolve_base_url("custom", "https://api.deepseek.com/v1/") == "https://api.deepseek.com/v1"


def test_decrypt_api_key_roundtrip():
    encrypted = encryptor.encrypt("sk-test-key")
    assert decrypt_api_key({"api_key_encrypted": encrypted}) == "sk-test-key"
    assert decrypt_api_key({}) is None


def test_resolve_api_key_for_list_priority():
    encrypted = encryptor.encrypt("stored-key")
    ai = {"api_key_encrypted": encrypted}
    assert resolve_api_key_for_list(ai, "temp-key") == "temp-key"
    assert resolve_api_key_for_list(ai, None) == "stored-key"


def test_resolve_api_key_for_list_missing():
    with pytest.raises(HTTPException) as exc:
        resolve_api_key_for_list({}, None)
    assert exc.value.status_code == 400


def test_provider_registry_rejects_empty_api_key():
    with pytest.raises(ValueError, match="API key"):
        ProviderRegistry.create_client("openai", "", "gpt-4o", None)


def test_provider_registry_custom_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        ProviderRegistry.create_client("custom", "sk-x", "gpt-4o", None)


def test_openai_compatible_client_rejects_empty_key():
    with pytest.raises(ValueError):
        OpenAICompatibleClient("", "https://api.openai.com/v1", "gpt-4o")


def test_filter_openai_models_response():
    data = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "gpt-3.5-turbo"},
            {"object": "model"},
        ],
    }
    models = _filter_openai_models(data)
    assert [m.id for m in models] == ["gpt-4o", "gpt-3.5-turbo"]


@pytest.mark.asyncio
async def test_list_models_openai_mock():
    from unittest.mock import patch

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"data": [{"id": "gpt-4o"}, {"id": "text-embedding-3-small"}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, headers=None):
            assert url.endswith("/models")
            return FakeResponse()

    client = OpenAICompatibleClient("sk-test", "https://api.openai.com/v1", "gpt-4o")
    with patch("apps.ai.client.httpx.AsyncClient", return_value=FakeClient()):
        models, error = await client.list_models()
    assert error is None
    assert len(models) == 2
    assert models[0].id == "gpt-4o"
