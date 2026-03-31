"""
SentinelX - 认证相关Schema
"""
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 过期时间(秒)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=256)
    password: str = Field(..., min_length=8, max_length=128)
    phone: Optional[str] = None
    tenant_id: int = Field(..., gt=0)


class TokenPayload(BaseModel):
    sub: int  # user_id
    tenant_id: int
    exp: int
    type: str  # access / refresh
