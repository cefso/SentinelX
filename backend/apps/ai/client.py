"""
SentinelX - AI服务
LLM客户端封装，支持 OpenAI 兼容、Claude、Qwen 等
"""
import httpx
from typing import Optional, Dict, Any, List, Tuple
from abc import ABC, abstractmethod
import structlog

from apps.core.config import settings
from apps.ai.schemas import ModelInfo
from apps.ai.providers import resolve_base_url, PROVIDER_PRESETS

logger = structlog.get_logger()


class LLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    async def list_models(self) -> Tuple[List[ModelInfo], Optional[str]]:
        """返回 (models, error)"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        pass


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _filter_openai_models(data: dict) -> List[ModelInfo]:
    models = []
    for item in data.get("data", []):
        mid = item.get("id") if isinstance(item, dict) else None
        if not mid:
            continue
        models.append(ModelInfo(id=mid, name=mid))
    return models


class OpenAICompatibleClient(LLMClient):
    """OpenAI 兼容 API（OpenAI / DeepSeek / Custom / Ollama 等）"""

    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o"):
        if not api_key or not str(api_key).strip():
            raise ValueError("API key is required")
        self.api_key = api_key.strip()
        self.base_url = _normalize_base_url(base_url)
        self.model = model

    async def list_models(self) -> Tuple[List[ModelInfo], Optional[str]]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 401:
                    return [], "Invalid API Key"
                if response.status_code >= 400:
                    return [], f"Upstream error: {response.status_code}"
                return _filter_openai_models(response.json()), None
        except Exception as e:
            logger.error("openai_list_models_error", error=str(e))
            return [], str(e)

    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return await self.chat(messages, temperature, max_tokens)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                result = response.json()

            if response.status_code == 401:
                return "", "Invalid API Key"
            if "error" in result:
                err = result["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return "", msg

            return result["choices"][0]["message"]["content"], None

        except Exception as e:
            logger.error("openai_generate_error", error=str(e))
            return "", str(e)


class AnthropicClient(LLMClient):
    """Anthropic Claude客户端"""

    def __init__(self, api_key: str, base_url: str = None, model: str = "claude-3-5-sonnet-20241022"):
        if not api_key or not str(api_key).strip():
            raise ValueError("API key is required")
        self.api_key = api_key.strip()
        self.base_url = _normalize_base_url(base_url or "https://api.anthropic.com/v1")
        self.model = model

    async def list_models(self) -> Tuple[List[ModelInfo], Optional[str]]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                if response.status_code == 401:
                    return [], "Invalid API Key"
                if response.status_code >= 400:
                    return [], f"Upstream error: {response.status_code}"
                data = response.json()
                models = []
                for item in data.get("data", []):
                    mid = item.get("id") if isinstance(item, dict) else None
                    if mid:
                        models.append(ModelInfo(id=mid, name=mid))
                return models, None
        except Exception as e:
            logger.error("anthropic_list_models_error", error=str(e))
            return [], str(e)

    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        messages = [{"role": "user", "content": prompt}]
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "system": system or "",
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                result = response.json()

            if response.status_code == 401:
                return "", "Invalid API Key"
            if "error" in result:
                err = result["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return "", msg

            return result["content"][0]["text"], None

        except Exception as e:
            logger.error("anthropic_generate_error", error=str(e))
            return "", str(e)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        return await self.generate(
            prompt=messages[-1]["content"] if messages else "",
            system="You are a helpful assistant.",
            temperature=temperature,
            max_tokens=max_tokens,
        )


class QwenClient(LLMClient):
    """阿里云 Qwen（DashScope）"""

    def __init__(self, api_key: str, base_url: str = None, model: str = "qwen-turbo"):
        if not api_key or not str(api_key).strip():
            raise ValueError("API key is required")
        self.api_key = api_key.strip()
        self.base_url = _normalize_base_url(base_url or "https://dashscope.aliyuncs.com/api/v1")
        self.model = model

    async def list_models(self) -> Tuple[List[ModelInfo], Optional[str]]:
        # DashScope 常用模型列表（无统一 list 接口时返回推荐集）
        known = [
            "qwen-max", "qwen-plus", "qwen-turbo", "qwen-long",
            "qwen2.5-72b-instruct", "qwen2.5-32b-instruct",
        ]
        return [ModelInfo(id=m, name=m) for m in known], None

    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/services/aigc/text-generation/generation",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": {"messages": messages},
                        "parameters": {
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    },
                )
                result = response.json()

            if response.status_code == 401:
                return "", "Invalid API Key"
            if "code" in result and result.get("code"):
                return "", result.get("message", "Unknown error")

            return result["output"]["text"], None

        except Exception as e:
            logger.error("qwen_generate_error", error=str(e))
            return "", str(e)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Tuple[str, Optional[str]]:
        return await self.generate(
            prompt=messages[-1]["content"] if messages else "",
            system=next((m["content"] for m in messages if m.get("role") == "system"), None),
            temperature=temperature,
            max_tokens=max_tokens,
        )


class ProviderRegistry:
    """根据 provider_id 创建客户端"""

    @staticmethod
    def is_openai_compatible(provider_id: str) -> bool:
        if provider_id in ("openai", "deepseek", "custom"):
            return True
        preset = next((p for p in PROVIDER_PRESETS if p["id"] == provider_id), None)
        return bool(preset and preset.get("openai_compatible"))

    @classmethod
    def create_client(
        cls,
        provider_id: str,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
    ) -> LLMClient:
        resolved_url = resolve_base_url(provider_id, base_url)

        if cls.is_openai_compatible(provider_id):
            if not resolved_url:
                raise ValueError("base_url is required for OpenAI-compatible provider")
            return OpenAICompatibleClient(api_key=api_key, base_url=resolved_url, model=model)

        if provider_id == "anthropic":
            return AnthropicClient(api_key=api_key, base_url=resolved_url or None, model=model)

        if provider_id == "qwen":
            return QwenClient(api_key=api_key, base_url=resolved_url or None, model=model)

        raise ValueError(f"Unknown LLM provider: {provider_id}")

    @classmethod
    async def list_models_for_provider(
        cls,
        provider_id: str,
        api_key: str,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
    ) -> Tuple[List[ModelInfo], Optional[str]]:
        resolved_url = resolve_base_url(provider_id, base_url)
        if cls.is_openai_compatible(provider_id) and not resolved_url:
            return [], "base_url is required"
        client = cls.create_client(provider_id, api_key, model, base_url)
        return await client.list_models()


class LLMFactory:
    """兼容旧工厂接口"""

    @classmethod
    def create_client(
        cls,
        provider: str = "openai",
        api_key: str = None,
        model: str = None,
        base_url: str = None,
    ) -> LLMClient:
        key = api_key or settings.OPENAI_API_KEY or ""
        if not key.strip():
            raise ValueError("API key is required")
        return ProviderRegistry.create_client(
            provider_id=provider,
            api_key=key,
            model=model or settings.AI_MODEL,
            base_url=base_url,
        )
