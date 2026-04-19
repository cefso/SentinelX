"""
SentinelX - 通知路由
"""
import re
import secrets
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.core.database import get_db
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.alert.models import Alert
from apps.rule.models import NotificationRecord
from apps.rule.models import NotificationChannel, NotificationTemplate
from apps.notify.schemas import (
    ChannelCreate, ChannelUpdate, ChannelResponse, ChannelTypeInfo, ChannelTypesResponse,
    ChannelTestRequest, ChannelTestResponse,
    NotificationRecordResponse, NotificationListResponse,
    TemplateCreate, TemplateUpdate, TemplateResponse,
    _validate_config_by_type,
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知渠道列表"""
    query = select(NotificationChannel).where(NotificationChannel.tenant_id == str(tenant_id))
    if is_active is not None:
        query = query.where(NotificationChannel.is_active == is_active)
    if channel_type:
        query = query.where(NotificationChannel.channel_type == channel_type)
    result = await db.execute(query.order_by(NotificationChannel.id))
    return result.scalars().all()


@router.post("/channels", response_model=ChannelResponse)
async def create_channel(
    request: ChannelCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建通知渠道"""
    # 检查 code 是否重复
    existing = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.tenant_id == str(tenant_id),
            NotificationChannel.code == request.code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"渠道代码 '{request.code}' 已存在")

    channel = NotificationChannel(
        tenant_id=str(tenant_id),
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知渠道详情"""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == str(tenant_id),
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新通知渠道"""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == str(tenant_id),
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # 如果更新 code，检查重复
    if request.code is not None and request.code != channel.code:
        existing = await db.execute(
            select(NotificationChannel).where(
                NotificationChannel.tenant_id == str(tenant_id),
                NotificationChannel.code == request.code,
                NotificationChannel.id != channel_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"渠道代码 '{request.code}' 已存在")

    # 如果更新 config，使用现有 channel_type 进行验证
    if request.config is not None:
        _validate_config_by_type(channel.channel_type, request.config)

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """删除通知渠道"""
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == str(tenant_id),
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """测试发送通知到指定渠道（走MQ队列）"""
    from apps.core.mq import get_mq_async

    # 获取渠道配置
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == str(tenant_id),
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if not channel.is_active:
        return ChannelTestResponse(success=False, error="Channel is inactive")

    # 获取模板
    from sqlalchemy import or_
    template_result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.channel_type == channel.channel_type,
            NotificationTemplate.is_active == True,
            or_(
                NotificationTemplate.tenant_id == str(tenant_id),
                NotificationTemplate.is_default == True,
            ),
        ).order_by(NotificationTemplate.is_default.desc())
    )
    template = template_result.scalar_one_or_none()
    template_content = template.content if template else None

    # 创建测试通知记录
    record = NotificationRecord(
        tenant_id=str(tenant_id),
        alert_id=0,  # 测试消息没有真实alert_id
        channel_id=channel_id,
        channel_type=channel.channel_type,
        status="pending",
        request_data={
            "is_test": True,
            "content": request.content or f"这是一条来自 {channel.name} 渠道的测试消息",
            "title": request.content or f"[测试消息] {channel.name}",
            "channel_config": channel.config,
            "template_content": template_content,
        },
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # 发送测试消息到MQ
    mq = await get_mq_async()
    await mq.send("alerts_notify", {
        "record_id": record.id,
        "is_test": True,
        "tenant_id": tenant_id,
        "channel_id": channel_id,
        "channel_type": channel.channel_type,
        "channel_config": channel.config,
        "content": request.content or f"这是一条来自 {channel.name} 渠道的测试消息",
        "title": request.content or f"[测试消息] {channel.name}",
        "template_content": template_content,
    })

    return ChannelTestResponse(
        success=True,
        error=None,
        response_data={"channel_type": channel.channel_type, "channel_name": channel.name, "queued": True, "record_id": record.id},
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知记录（支持分页）"""
    query = select(NotificationRecord).where(NotificationRecord.tenant_id == str(tenant_id))

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

# ============ 模板变量说明 ============

class TemplateVariable(BaseModel):
    """模板变量"""
    name: str = Field(..., description="变量名（不含 {{ }}）")
    description: str = Field(..., description="变量说明")
    example: Optional[str] = Field(None, description="使用示例")
    category: str = Field(..., description="分类: common/metric/raw_data/channel")


class TemplateVariablesResponse(BaseModel):
    """模板变量说明响应"""
    channel_type: str
    variables: List[TemplateVariable]


# 通用变量（所有渠道）
COMMON_VARIABLES = [
    TemplateVariable(name="alert.title", description="告警标题", category="common"),
    TemplateVariable(name="alert.content", description="告警内容", category="common"),
    TemplateVariable(name="alert.severity", description="严重级别 (critical/high/medium/low/info)", category="common"),
    TemplateVariable(name="alert.status", description="告警状态 (firing/resolved)", category="common"),
    TemplateVariable(name="alert.source", description="告警来源", category="common"),
    TemplateVariable(name="alert.fired_at", description="触发时间 (ISO格式)", category="common"),
    TemplateVariable(name="alert.fire_count", description="触发次数", category="common"),
    TemplateVariable(name="alert.labels.xxx", description="提取标签字段 (如 alert.labels.env)", category="common"),
    TemplateVariable(name="alert.annotations.xxx", description="提取注解字段 (如 alert.annotations.runbook)", category="common"),
    TemplateVariable(name="alert_key", description="告警唯一标识", category="common"),
    TemplateVariable(name="alert_id", description="告警ID", category="common"),
]

# 指标类变量
METRIC_VARIABLES = [
    TemplateVariable(name="alert.namespace", description="命名空间/云产品", category="metric"),
    TemplateVariable(name="alert.instance_name", description="实例名称", category="metric"),
    TemplateVariable(name="alert.instance_id", description="实例ID", category="metric"),
    TemplateVariable(name="alert.metric_name", description="指标名称", category="metric"),
    TemplateVariable(name="alert.metric_value", description="指标值", category="metric"),
]

# 原始数据变量
RAW_DATA_VARIABLES = [
    TemplateVariable(name="alert.raw_data", description="原始告警数据（dict）", category="raw_data"),
    TemplateVariable(name="alert.raw_data.xxx", description="提取原始数据中的任意字段", category="raw_data", example="{{ alert.raw_data.cpu }}"),
    TemplateVariable(name="alert.extra_data", description="扩展数据（dict）", category="raw_data"),
    TemplateVariable(name="alert.extra_data.xxx", description="提取扩展数据中的任意字段", category="raw_data"),
]

# 特殊渠道变量
CHANNEL_VARIABLES = [
    TemplateVariable(name="alert.fingerprint", description="告警指纹（钉钉/飞书/企微等渠道适用）", category="channel"),
]


@router.get("/templates/variables/{channel_type}", response_model=TemplateVariablesResponse)
async def get_template_variables(channel_type: str):
    """获取指定渠道类型的模板可用变量说明"""
    if channel_type not in ["dingtalk", "feishu", "wecom", "email", "webhook", "slack"]:
        raise HTTPException(status_code=400, detail=f"Unsupported channel type: {channel_type}")

    variables = list(COMMON_VARIABLES)
    variables.extend(METRIC_VARIABLES)
    variables.extend(RAW_DATA_VARIABLES)
    variables.extend(CHANNEL_VARIABLES)

    return TemplateVariablesResponse(channel_type=channel_type, variables=variables)


@router.get("/templates/variables", response_model=List[TemplateVariablesResponse])
async def list_all_template_variables():
    """获取所有渠道类型的模板变量说明"""
    all_types = ["dingtalk", "feishu", "wecom", "email", "webhook", "slack"]
    return [
        TemplateVariablesResponse(
            channel_type=ct,
            variables=list(COMMON_VARIABLES) + list(METRIC_VARIABLES) + list(RAW_DATA_VARIABLES) + list(CHANNEL_VARIABLES),
        )
        for ct in all_types
    ]


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    channel_type: Optional[str] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取通知模板列表"""
    query = select(NotificationTemplate).where(NotificationTemplate.tenant_id == str(tenant_id))
    if channel_type:
        query = query.where(NotificationTemplate.channel_type == channel_type)
    result = await db.execute(query.order_by(NotificationTemplate.id))
    return result.scalars().all()


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建通知模板"""
    # 自动生成 code（如果未提供）
    import re
    import secrets
    code = request.code
    if not code:
        # 判断 name 是否含中文字符
        if re.search(r'[\u4e00-\u9fff]', request.name):
            # 中文名：用随机短码
            code = f"tmpl_{secrets.token_hex(4)}"
        else:
            # 英文名：slugify
            slug = re.sub(r'[^a-zA-Z0-9]', '_', request.name).lower()
            code = f"tmpl_{slug}"
    # 检查 code 是否重复
    existing = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.tenant_id == str(tenant_id),
            NotificationTemplate.code == code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"模板代码 '{code}' 已存在")

    template = NotificationTemplate(
        tenant_id=str(tenant_id),
        name=request.name,
        code=code,
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取模板详情"""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == str(tenant_id),
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新通知模板"""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == str(tenant_id),
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
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """删除通知模板"""
    result = await db.execute(
        select(NotificationTemplate).where(
            NotificationTemplate.id == template_id,
            NotificationTemplate.tenant_id == str(tenant_id),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()
    return {"message": "Template deleted successfully"}
