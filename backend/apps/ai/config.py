"""
SentinelX - 租户 AI 配置读写
"""
from dataclasses import dataclass
from typing import Optional, Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.tenant.models import Tenant
from apps.core.security import encryptor
from apps.ai.schemas import AIConfigResponse, AIConfigUpdate
from apps.ai.providers import PROVIDER_PRESETS, resolve_base_url
from apps.ai.prompts import (
    PROMPT_META,
    DEFAULT_PROMPTS,
    normalize_prompts_for_save,
    prompts_for_response,
    custom_prompts_from_blob,
)


AI_CONFIG_KEY = "ai"


@dataclass
class TenantAIConfig:
    provider_id: str
    display_name: str
    base_url: str
    model: str
    api_key: str
    enabled: bool
    prompts: dict


def _preset_display_name(provider_id: str) -> str:
    for p in PROVIDER_PRESETS:
        if p["id"] == provider_id:
            return p["name"]
    return provider_id


def _ai_blob_from_tenant(tenant: Tenant) -> dict:
    config = tenant.config or {}
    ai = config.get(AI_CONFIG_KEY)
    if not isinstance(ai, dict):
        return {}
    return ai


def _merge_tenant_config(tenant: Tenant, ai_blob: dict) -> None:
    config = dict(tenant.config or {})
    config[AI_CONFIG_KEY] = ai_blob
    tenant.config = config


async def get_tenant_row(db: AsyncSession, tenant_id: int) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


def to_response(ai: dict) -> AIConfigResponse:
    provider_id = ai.get("provider_id") or "openai"
    return AIConfigResponse(
        provider_id=provider_id,
        display_name=ai.get("display_name") or _preset_display_name(provider_id),
        base_url=ai.get("base_url"),
        model=ai.get("model") or "",
        api_key_set=bool(ai.get("api_key_encrypted")),
        enabled=bool(ai.get("enabled", False)),
        prompts=prompts_for_response(ai),
        prompt_defaults=dict(DEFAULT_PROMPTS),
        prompt_meta=[{"key": m["key"], "title": m["title"], "description": m.get("description", "")} for m in PROMPT_META],
    )


async def load_ai_config_response(db: AsyncSession, tenant_id: int) -> AIConfigResponse:
    tenant = await get_tenant_row(db, tenant_id)
    return to_response(_ai_blob_from_tenant(tenant))


async def save_ai_config(
    db: AsyncSession,
    tenant_id: int,
    body: AIConfigUpdate,
) -> AIConfigResponse:
    tenant = await get_tenant_row(db, tenant_id)
    ai = dict(_ai_blob_from_tenant(tenant))

    preset = next((p for p in PROVIDER_PRESETS if p["id"] == body.provider_id), None)
    if not preset and body.provider_id != "custom":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {body.provider_id}",
        )

    base_url = resolve_base_url(body.provider_id, body.base_url)
    if preset and preset.get("requires_base_url") and not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_url is required for this provider",
        )

    if body.api_key and body.api_key.strip():
        ai["api_key_encrypted"] = encryptor.encrypt(body.api_key.strip())
    elif not ai.get("api_key_encrypted"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key is required",
        )

    ai["provider_id"] = body.provider_id
    ai["display_name"] = body.display_name or _preset_display_name(body.provider_id)
    ai["base_url"] = body.base_url if body.provider_id == "custom" else body.base_url
    if body.provider_id != "custom" and preset and preset.get("default_base_url") and not ai.get("base_url"):
        ai["base_url"] = preset["default_base_url"]
    ai["model"] = body.model
    ai["enabled"] = body.enabled

    if body.prompts is not None:
        ai["prompts"] = normalize_prompts_for_save(body.prompts)

    _merge_tenant_config(tenant, ai)
    await db.commit()
    await db.refresh(tenant)
    return to_response(ai)


def decrypt_api_key(ai: dict) -> Optional[str]:
    enc = ai.get("api_key_encrypted")
    if not enc:
        return None
    try:
        return encryptor.decrypt(enc)
    except Exception:
        return None


async def resolve_tenant_ai_config(db: AsyncSession, tenant_id: int) -> TenantAIConfig:
    tenant = await get_tenant_row(db, tenant_id)
    ai = _ai_blob_from_tenant(tenant)

    if not ai.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI is not configured for this tenant",
        )

    api_key = decrypt_api_key(ai)
    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI is not configured for this tenant",
        )

    provider_id = ai.get("provider_id") or "openai"
    model = ai.get("model")
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI model is not configured for this tenant",
        )

    base_url = resolve_base_url(provider_id, ai.get("base_url"))

    return TenantAIConfig(
        provider_id=provider_id,
        display_name=ai.get("display_name") or _preset_display_name(provider_id),
        base_url=base_url,
        model=model,
        api_key=api_key.strip(),
        enabled=True,
        prompts=custom_prompts_from_blob(ai),
    )


def resolve_api_key_for_list(
    ai: dict,
    request_api_key: Optional[str],
) -> str:
    if request_api_key and request_api_key.strip():
        return request_api_key.strip()
    key = decrypt_api_key(ai)
    if key and key.strip():
        return key.strip()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="API Key is required to list models",
    )
