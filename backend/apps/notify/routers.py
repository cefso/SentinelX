"""
SentinelX - 通知路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.core.database import get_db
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.alert.models import Alert
from apps.notify.models import NotificationRecord
from apps.rule.models import NotificationChannel, NotificationTemplate
from apps.notify.schemas import (
    ChannelCreate, ChannelUpdate, ChannelResponse, ChannelTypeInfo, ChannelTypesResponse,
    ChannelTestRequest, ChannelTestResponse,
    NotificationRecordResponse, NotificationListResponse,
    TemplateCreate, TemplateUpdate, TemplateResponse,
)
from apps.notify.channels import ChannelFactory

router = APIRouter()


# ============ 渠道类型信息 ============

CHANNEL_TYPES = [
    ChannelTypeInfo(
        value="dingtalk", label="钉钉", icon="🔔",
        required_fields=["webhook_url"],
        optional_fields=["secret"],
        description="钉钉群机器人，支持加签模式",
    ),
    ChannelTypeInfo(
        value="feishu", label="飞书", icon="✈️",
        required_fields=["webhook_url"],
        optional_fields=[],
        description="飞书群机器人",
    ),
    ChannelTypeInfo(
        value="wecom", label="企业微信", icon="💬",
        required_fields=["webhook_url"],
        optional_fields=[],
        description="企业微信群机器人",
    ),
    ChannelTypeInfo(
        value="email", label="邮件", icon="📧",
        required_fields=["smtp_host", "smtp_port", "username", "password", "from_addr", "recipients"],
        optional_fields=[],
        description="SMTP邮件通知",
    ),
    ChannelTypeInfo(
        value="webhook", label="Webhook", icon="🔗",
        required_fields=["webhook_url"],
        optional_fields=["headers"],
        description="通用HTTP Webhook",
    ),
    ChannelTypeInfo(
        value="slack", label="Slack", icon="💬",
        required_fields=["webhook_url"],
        optional_fields=[],
        description="Slack Incoming Webhook",
    ),
]


# ============ 通知渠道管理 ============

@router.get("/channel-types", response_model=ChannelTypesResponse)
async def list_channel_types():
    """获取支持的渠道类型列表"""
    return ChannelTypesResponse(items=CHANNEL_TYPES)


@router.get("/channels", response_model=List[ChannelResponse])
async def list_channels(
    is_active: Optional[bool] = None,
    channel_type: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知渠道列表"""
    query = select(NotificationChannel).where(NotificationChannel.tenant_id == tenant_id)
    if is_active is not None:
        query = query.where(NotificationChannel.is_active == is_active)
    if channel_type:
        query = query.where(NotificationChannel.channel_type == channel_type)
    result = await db.execute(query.order_by(NotificationChannel.id))
    return result.scalars().all()


@router.post("/channels", response_model=ChannelResponse)
async def create_channel(
    request: ChannelCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建通知渠道"""
    # 检查 code 是否重复
    existing = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.tenant_id == tenant_id,
            NotificationChannel.code == request.code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"渠道代码 '{request.code}' 已存在")

    channel = NotificationChannel(
        tenant_id=tenant_id,
        name=request.name,
        code=request.code,
        channel_type=request.channel_type,
        config=request.config,
        is_active=request.is_active,
        is_default=request.is_default,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知渠道详情"""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    request: ChannelUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新通知渠道"""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # 如果更新 code，检查重复
    if request.code is not None and request.code != channel.code:
        existing = await db.execute(
            select(NotificationChannel).where(
                NotificationChannel.tenant_id == tenant_id,
                NotificationChannel.code == request.code,
                NotificationChannel.id != channel_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"渠道代码 '{request.code}' 已存在")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """删除通知渠道"""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    await db.delete(channel)
    await db.commit()
    return {"message": "Channel deleted successfully"}


@router.post("/channels/{channel_id}/test", response_model=ChannelTestResponse)
async def test_channel(
    channel_id: int,
    request: ChannelTestRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """测试发送通知到指定渠道"""
    # 获取渠道配置
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel.is_active:
        return ChannelTestResponse(success=False, error="Channel is inactive")

    # 创建模拟告警用于测试
    test_alert = Alert(
        tenant_id=tenant_id,
        alert_key=f"test-channel-{channel_id}",
        fingerprint=f"test-fp-{channel_id}",
        source="test",
        title=request.content or f"[测试消息] {channel.name}",
        content=request.content or f"这是一条来自 {channel.name} 渠道的测试消息",
        severity="info",
        status="firing",
        labels={},
        annotations={},
    )
    # 设置fire_count等属性以满足格式要求
    test_alert.fire_count = 1

    # 获取模板
    from sqlalchemy import or_
    template_result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.channel_type == channel.channel_type,
            NotificationTemplate.is_active == True,
            or_(
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.is_default == True,
            ),
        ).order_by(NotificationTemplate.is_default == False)
    )
    template = template_result.scalar_one_or_none()
    template_content = template.content if template else None

    # 发送测试通知
    success, error = ChannelFactory.send_alert(
        channel.channel_type,
        channel.config,
        test_alert,
        template_content,
    )

    return ChannelTestResponse(
        success=success,
        error=error,
        response_data={"channel_type": channel.channel_type, "channel_name": channel.name},
    )


# ============ 通知记录 ============

@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    alert_id: Optional[int] = None,
    status: Optional[str] = None,
    channel_type: Optional[str] = None,
    channel_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知记录（支持分页）"""
    query = select(NotificationRecord).where(NotificationRecord.tenant_id == tenant_id)

    if alert_id is not None:
        query = query.where(NotificationRecord.alert_id == alert_id)
    if status:
        query = query.where(NotificationRecord.status == status)
    if channel_type:
        query = query.where(NotificationRecord.channel_type == channel_type)
    if channel_id is not None:
        query = query.where(NotificationRecord.channel_id == channel_id)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(NotificationRecord.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return NotificationListResponse(items=list(items), total=total, limit=limit, offset=offset)


# ============ 通知模板管理 ============

@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    channel_type: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知模板列表"""
    query = select(NotificationTemplate).where(NotificationTemplate.tenant_id == tenant_id)
    if channel_type:
        query = query.where(NotificationTemplate.channel_type == channel_type)
    result = await db.execute(query.order_by(NotificationTemplate.id))
    return result.scalars().all()


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建通知模板"""
    # 检查 code 是否重复
    existing = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == tenant_id,
            NotificationTemplate.code == request.code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"模板代码 '{request.code}' 已存在")

    template = NotificationTemplate(
        tenant_id=tenant_id,
        name=request.name,
        code=request.code,
        channel_type=request.channel_type,
        content=request.content,
        variables=request.variables,
        is_active=request.is_active,
        is_default=request.is_default,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取模板详情"""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    request: TemplateUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新通知模板"""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """删除通知模板"""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == tenant_id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()
    return {"message": "Template deleted successfully"}
