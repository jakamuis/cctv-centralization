from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.schemas.alerts import Alert, AlertList, AlertFilterParams
from app.services.alerts import AlertService
from app.api.v1.dependencies import get_db

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=AlertList, summary="List alerts with filtering and pagination")
async def list_alerts(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_id: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = AlertService(db)
    filter_params = AlertFilterParams(
        device_id=device_id,
        site_id=site_id,
        alert_type=alert_type,
        severity=severity,
        status=status,
        acknowledged=acknowledged,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    total = await service.count_alerts(filter_params)
    items = await service.list_alerts(filter_params)
    return AlertList(total=total, items=items)


@router.get("/{alert_id}", response_model=Alert, summary="Get alert details by ID")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    service = AlertService(db)
    alert = await service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=Alert, summary="Acknowledge an alert")
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    service = AlertService(db)
    alert = await service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.acknowledged:
        return alert
    updated_alert = await service.acknowledge_alert(alert)
    return updated_alert


@router.post("/{alert_id}/resolve", response_model=Alert, summary="Resolve (close) an alert")
async def resolve_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    service = AlertService(db)
    alert = await service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if not alert.active:
        return alert
    updated_alert = await service.resolve_alert(alert)
    return updated_alert