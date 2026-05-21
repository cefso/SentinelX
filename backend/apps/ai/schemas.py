"""
SentinelX - AI 配置 Schema
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str
    name: Optional[str] = None


class ProviderMeta(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    default_base_url: Optional[str] = None
    requires_base_url: bool = False
    openai_compatible: bool = False


class AIPromptMeta(BaseModel):
    key: str
    title: str
    description: str = ""


class AIConfigResponse(BaseModel):
    provider_id: str = "openai"
    display_name: str = "OpenAI"
    base_url: Optional[str] = None
    model: str = ""
    api_key_set: bool = False
    enabled: bool = False
    prompts: Dict[str, Optional[str]] = Field(default_factory=dict)
    prompt_defaults: Dict[str, str] = Field(default_factory=dict)
    prompt_meta: List[AIPromptMeta] = Field(default_factory=list)


class AIConfigUpdate(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=64)
    display_name: Optional[str] = Field(None, max_length=128)
    base_url: Optional[str] = Field(None, max_length=512)
    model: str = Field(..., min_length=1, max_length=128)
    api_key: Optional[str] = Field(None, max_length=512)
    enabled: bool = True
    prompts: Optional[Dict[str, Optional[str]]] = None


class ListModelsRequest(BaseModel):
    provider_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ListModelsResponse(BaseModel):
    models: List[ModelInfo]


class ProvidersListResponse(BaseModel):
    providers: List[ProviderMeta]


class AITaskCreateResponse(BaseModel):
    task_id: str
    status: str = "pending"
    alert_id: int
    action: str


class AITaskStatusResponse(BaseModel):
    task_id: str
    status: str
    alert_id: int
    action: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
