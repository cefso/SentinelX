"""
SentinelX - AI服务
LLM客户端封装，支持 OpenAI、Claude、Qwen 等
"""
import json
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import structlog

from apps.core.config import settings

logger = structlog.get_logger()


class LLMClient(ABC):
    """LLM客户端基类"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """
        生成文本
        返回: (生成的文本, 错误信息)
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """
        对话
        返回: (回复文本, 错误信息)
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI客户端"""

    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """生成文本"""
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

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

            if "error" in result:
                return "", result["error"].get("message", "Unknown error")

            return result["choices"][0]["message"]["content"], None

        except Exception as e:
            logger.error("openai_generate_error", error=str(e))
            return "", str(e)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """对话"""
        import httpx

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

            if "error" in result:
                return "", result["error"].get("message", "Unknown error")

            return result["choices"][0]["message"]["content"], None

        except Exception as e:
            logger.error("openai_chat_error", error=str(e))
            return "", str(e)


class AnthropicClient(LLMClient):
    """Anthropic Claude客户端"""

    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"

    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """生成文本"""
        import httpx

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
                        "system": system,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                result = response.json()

            if "error" in result:
                return "", result["error"].get("message", "Unknown error")

            return result["content"][0]["text"], None

        except Exception as e:
            logger.error("anthropic_generate_error", error=str(e))
            return "", str(e)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """对话"""
        # Anthropic uses messages format similar to OpenAI
        return await self.generate(
            prompt=messages[-1]["content"] if messages else "",
            system="You are a helpful assistant.",
            temperature=temperature,
            max_tokens=max_tokens,
        )


class QwenClient(LLMClient):
    """阿里云Qwen客户端"""

    def __init__(self, api_key: str = None, model: str = "qwen-turbo"):
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"

    async def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """生成文本"""
        import httpx

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

            if "error" in result:
                return "", result["error"].get("message", "Unknown error")

            return result["output"]["text"], None

        except Exception as e:
            logger.error("qwen_generate_error", error=str(e))
            return "", str(e)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """对话"""
        import httpx

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

            if "error" in result:
                return "", result["error"].get("message", "Unknown error")

            return result["output"]["text"], None

        except Exception as e:
            logger.error("qwen_chat_error", error=str(e))
            return "", str(e)


class LLMFactory:
    """LLM工厂"""

    _clients: Dict[str, type] = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "qwen": QwenClient,
    }

    @classmethod
    def create_client(
        cls,
        provider: str = "openai",
        api_key: str = None,
        model: str = None,
    ) -> LLMClient:
        """创建LLM客户端"""
        client_class = cls._clients.get(provider.lower())
        if not client_class:
            raise ValueError(f"Unknown LLM provider: {provider}")

        return client_class(api_key=api_key, model=model)

    @classmethod
    def generate_text(
        cls,
        provider: str,
        prompt: str,
        system: str = None,
        api_key: str = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> tuple[str, Optional[str]]:
        """快捷文本生成"""
        client = cls.create_client(provider, api_key, model)
        return client.generate(prompt, system, temperature, max_tokens)
