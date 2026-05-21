"""
SentinelX - AI 提供商预设元数据
"""
from typing import Optional, List, Dict, Any

from apps.ai.schemas import ProviderMeta


PROVIDER_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "openai",
        "name": "OpenAI",
        "description": "OpenAI 官方 API",
        "default_base_url": "https://api.openai.com/v1",
        "requires_base_url": False,
        "openai_compatible": True,
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "description": "DeepSeek OpenAI 兼容接口",
        "default_base_url": "https://api.deepseek.com/v1",
        "requires_base_url": False,
        "openai_compatible": True,
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "description": "Anthropic Messages API",
        "default_base_url": "https://api.anthropic.com/v1",
        "requires_base_url": False,
        "openai_compatible": False,
    },
    {
        "id": "qwen",
        "name": "阿里云 Qwen",
        "description": "DashScope 通义千问",
        "default_base_url": "https://dashscope.aliyuncs.com/api/v1",
        "requires_base_url": False,
        "openai_compatible": False,
    },
    {
        "id": "custom",
        "name": "自定义（OpenAI 兼容）",
        "description": "自建网关或第三方 OpenAI 兼容服务",
        "default_base_url": None,
        "requires_base_url": True,
        "openai_compatible": True,
    },
]


def resolve_base_url(provider_id: str, base_url: Optional[str]) -> str:
    if provider_id == "custom":
        if not base_url or not base_url.strip():
            return ""
        return base_url.strip().rstrip("/")

    preset = next((p for p in PROVIDER_PRESETS if p["id"] == provider_id), None)
    if base_url and base_url.strip():
        return base_url.strip().rstrip("/")
    if preset and preset.get("default_base_url"):
        return preset["default_base_url"].rstrip("/")
    if preset and preset.get("openai_compatible"):
        return "https://api.openai.com/v1"
    return ""


def list_provider_metas() -> List[ProviderMeta]:
    return [ProviderMeta(**p) for p in PROVIDER_PRESETS]
