"""
SentinelX - 规则管理路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.core.database import get_db
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.rule.models import AlertRule, NotificationChannel, NotificationTemplate
from apps.rule.schemas import (
    RuleCreate, RuleUpdate, RuleResponse, RuleTestRequest, RuleTestResponse,
    ChannelCreate, ChannelUpdate, ChannelResponse,
    TemplateCreate, TemplateUpdate, TemplateResponse,
)

router = APIRouter()


# ============ 规则管理 ============

@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(
    is_active: Optional[bool] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取规则列表"""
    query = select(AlertRule).where(AlertRule.tenant_id == str(tenant_id))
    if is_active is not None:
        query = query.where(AlertRule.is_active == is_active)
    query = query.order_by(AlertRule.priority.desc(), AlertRule.id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    request: RuleCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """创建规则"""
    rule = AlertRule(
        tenant_id=str(tenant_id),
        name=request.name,
        code=request.code,
        description=request.description,
        conditions=[c.model_dump() for c in request.conditions],
        condition_mode=request.condition_mode,
        actions=request.actions,
        priority=request.priority,
        is_active=request.is_active,
        suppress_config=request.suppress_config,
        aggregate_config=request.aggregate_config,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """获取规则详情"""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == str(tenant_id)
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    request: RuleUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """更新规则"""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == str(tenant_id)
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = request.model_dump(exclude_unset=True)
    if "conditions" in update_data:
        update_data["conditions"] = [c.model_dump() if hasattr(c, 'model_dump') else c for c in update_data["conditions"]]

    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """删除规则"""
    result = await db.execute(
        select(AlertRule).where(
            AlertRule.id == rule_id,
            AlertRule.tenant_id == str(tenant_id)
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
    return {"message": "Rule deleted successfully"}


@router.post("/rules/test", response_model=RuleTestResponse)
async def test_rule(
    request: RuleTestRequest,
    tenant_id: int = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """测试规则条件"""
    from apps.rule.engine import RuleEngine

    engine = RuleEngine()
    matched, reason, evaluated = engine.evaluate_conditions(
        request.conditions,
        request.condition_mode,
        request.test_data
    )

    return RuleTestResponse(
        matched=matched,
        reason=reason,
        evaluated_conditions=evaluated,
    )


# ============ 通知渠道管理 ============

@router.get("/channels", response_model=list[ChannelResponse])
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
            NotificationChannel.tenant_id == str(tenant_id)
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)

    await db.commit()
    await db.refresh(channel)
    return channel


# ============ 通知模板管理 ============

@router.get("/templates", response_model=list[TemplateResponse])
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
    template = NotificationTemplate(
        tenant_id=str(tenant_id),
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
            NotificationTemplate.tenant_id == str(tenant_id)
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
