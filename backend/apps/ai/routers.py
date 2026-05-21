"""
SentinelX - AI路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from apps.core.database import get_db
from apps.core.redis import get_redis
from apps.auth.dependencies import get_current_tenant_id, get_current_user, require_superuser
from apps.tenant.models import User
from apps.ai.schemas import (
    AIConfigResponse,
    AIConfigUpdate,
    ListModelsRequest,
    ListModelsResponse,
    ProvidersListResponse,
    AITaskCreateResponse,
    AITaskStatusResponse,
)
from apps.ai.config import (
    load_ai_config_response,
    save_ai_config,
    get_tenant_row,
    _ai_blob_from_tenant,
    resolve_api_key_for_list,
)
from apps.ai.providers import list_provider_metas, resolve_base_url
from apps.ai.client import ProviderRegistry
from apps.ai.tasks import submit_alert_ai_task, get_ai_task_for_tenant

router = APIRouter()


@router.get("/ai/config", response_model=AIConfigResponse)
async def get_ai_config(
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser()),
):
    """获取当前租户 AI 配置（脱敏）"""
    return await load_ai_config_response(db, tenant_id)


@router.put("/ai/config", response_model=AIConfigResponse)
async def update_ai_config(
    body: AIConfigUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser()),
):
    """保存当前租户 AI 配置"""
    return await save_ai_config(db, tenant_id, body)


@router.get("/ai/providers", response_model=ProvidersListResponse)
async def get_ai_providers(
    current_user: User = Depends(get_current_user),
):
    """获取支持的 AI 提供商列表"""
    return ProvidersListResponse(providers=list_provider_metas())


@router.post("/ai/models", response_model=ListModelsResponse)
async def list_ai_models(
    body: ListModelsRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser()),
):
    """根据 API Key 拉取可用模型列表"""
    base_url = resolve_base_url(body.provider_id, body.base_url)
    if ProviderRegistry.is_openai_compatible(body.provider_id) and not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_url is required for this provider",
        )

    tenant = await get_tenant_row(db, tenant_id)
    ai = _ai_blob_from_tenant(tenant)
    api_key = resolve_api_key_for_list(ai, body.api_key)

    models, error = await ProviderRegistry.list_models_for_provider(
        provider_id=body.provider_id,
        api_key=api_key,
        base_url=body.base_url,
        model="gpt-4o",
    )
    if error:
        if "Invalid API Key" in error or "401" in error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error)

    return ListModelsResponse(models=models)


@router.get("/ai/tasks/{task_id}", response_model=AITaskStatusResponse)
async def get_ai_task_status(
    task_id: str,
    tenant_id: int = Depends(get_current_tenant_id),
    redis: Redis = Depends(get_redis),
):
    """查询告警 AI 异步任务状态与结果"""
    task = await get_ai_task_for_tenant(redis, task_id, tenant_id)
    return AITaskStatusResponse(**task)


@router.post(
    "/alerts/{alert_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AITaskCreateResponse,
)
async def analyze_alert(
    alert_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """根因分析（异步任务）"""
    data = await submit_alert_ai_task(db, redis, tenant_id, alert_id, "analyze")
    return AITaskCreateResponse(**data)


@router.post(
    "/alerts/{alert_id}/polish",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AITaskCreateResponse,
)
async def polish_alert_content(
    alert_id: int,
    template: Optional[str] = None,
    style: str = Query("formal", pattern="^(formal|simple|friendly)$"),
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """内容润色（异步任务）"""
    data = await submit_alert_ai_task(
        db, redis, tenant_id, alert_id, "polish",
        params={"template": template, "style": style},
    )
    return AITaskCreateResponse(**data)


@router.post(
    "/alerts/{alert_id}/suggest-actions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AITaskCreateResponse,
)
async def suggest_alert_actions(
    alert_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """建议操作（异步任务）"""
    data = await submit_alert_ai_task(db, redis, tenant_id, alert_id, "suggest-actions")
    return AITaskCreateResponse(**data)


@router.post(
    "/alerts/{alert_id}/predict-impact",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AITaskCreateResponse,
)
async def predict_alert_impact(
    alert_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """影响预测（异步任务）"""
    data = await submit_alert_ai_task(db, redis, tenant_id, alert_id, "predict-impact")
    return AITaskCreateResponse(**data)
