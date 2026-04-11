"""
SentinelX - 维护窗口路由
"""
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from apps.core.database import get_db
from apps.auth.dependencies import get_current_user, get_current_tenant_id
from apps.tenant.models import User
from apps.maintenance.service import MaintenanceService

router = APIRouter()


# ============ 维护窗口管理 ============

@router.get("/maintenance/windows")
async def list_maintenance_windows(
    active_only: bool = False,
    tenant_id: int = Depends(get_current_tenant_id),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取维护窗口列表"""
    service = MaintenanceService(db)
    windows = await service.list_windows(str(tenant_id), active_only=active_only)
    return {
        "total": len(windows),
        "items": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "start_time": w.start_time.isoformat(),
                "end_time": w.end_time.isoformat(),
                "scope": w.scope,
                "is_active": w.is_active,
                "suppressed_count": w.suppressed_count,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in windows
        ],
    }


@router.post("/maintenance/windows")
async def create_maintenance_window(
    name: str,
    start_time: datetime,
    end_time: datetime,
    description: Optional[str] = None,
    scope: Optional[Dict[str, Any]] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建维护窗口"""
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    service = MaintenanceService(db)
    window = await service.create_window(
        tenant_id=str(tenant_id),
        name=name,
        start_time=start_time,
        end_time=end_time,
        description=description,
        scope=scope,
    )

    return {
        "id": window.id,
        "name": window.name,
        "start_time": window.start_time.isoformat(),
        "end_time": window.end_time.isoformat(),
        "scope": window.scope,
        "is_active": window.is_active,
        "message": "Maintenance window created successfully",
    }


@router.get("/maintenance/windows/{window_id}")
async def get_maintenance_window(
    window_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取维护窗口详情"""
    service = MaintenanceService(db)
    window = await service.get_window(window_id, str(tenant_id))
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    return {
        "id": window.id,
        "name": window.name,
        "description": window.description,
        "start_time": window.start_time.isoformat(),
        "end_time": window.end_time.isoformat(),
        "scope": window.scope,
        "is_active": window.is_active,
        "suppressed_count": window.suppressed_count,
        "created_at": window.created_at.isoformat() if window.created_at else None,
        "updated_at": window.updated_at.isoformat() if window.updated_at else None,
    }


@router.put("/maintenance/windows/{window_id}")
async def update_maintenance_window(
    window_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    scope: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新维护窗口"""
    if end_time and start_time and end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    service = MaintenanceService(db)
    window = await service.update_window(
        window_id,
        str(tenant_id),
        name=name,
        description=description,
        start_time=start_time,
        end_time=end_time,
        scope=scope,
        is_active=is_active,
    )
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    return {
        "id": window.id,
        "name": window.name,
        "message": "Maintenance window updated successfully",
    }


@router.delete("/maintenance/windows/{window_id}")
async def delete_maintenance_window(
    window_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除维护窗口"""
    service = MaintenanceService(db)
    success = await service.delete_window(window_id, str(tenant_id))
    if not success:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    return {"message": "Maintenance window deleted successfully"}


@router.get("/maintenance/windows/{window_id}/check")
async def check_maintenance_status(
    window_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检查维护窗口当前状态"""
    service = MaintenanceService(db)
    window = await service.get_window(window_id, str(tenant_id))
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    now = datetime.utcnow()
    is_active = (
        window.is_active
        and window.start_time <= now
        and window.end_time >= now
    )

    return {
        "id": window.id,
        "name": window.name,
        "is_active": is_active,
        "is_within_window": window.start_time <= now <= window.end_time,
        "time_until_start": (window.start_time - now).total_seconds() if now < window.start_time else None,
        "time_until_end": (window.end_time - now).total_seconds() if now < window.end_time else None,
    }
