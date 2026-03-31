"""
SentinelX - 通知Schema
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class NotificationRecordResponse(BaseModel):
    id: int
    tenant_id: str
    alert_id: int
    channel_id: int
    channel_type: str
    status: str
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True
