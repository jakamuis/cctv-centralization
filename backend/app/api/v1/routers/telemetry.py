from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.schemas.telemetry import CurrentDeviceState, TelemetryHistory, TelemetryHistoryList, TelemetryFilterParams
from app.services.telemetry import TelemetryService
from app.api.v1.dependencies import get_db

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("/current/{device_id}", response_model=CurrentDeviceState, summary="Get latest device state")
async def get_latest_device_state(device_id: str, db: AsyncSession = Depends(get_db)):
    service = TelemetryService(db)
    state = await service.get_latest_device_state(device_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device state not found")
    return state


@router.get("/history", response_model=TelemetryHistoryList, summary="List historical telemetry with filters and pagination")
async def list_telemetry_history(
    device_id: str = Query(None),
    site_id: str = Query(None),
    status: str = Query(None),
    start_time: datetime = Query(None),
    end_time: datetime = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = TelemetryService(db)
    filter_params = TelemetryFilterParams(
        device_id=device_id,
        site_id=site_id,
        status=status,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )
    total = await service.count_telemetry_history(filter_params)
    items = await service.list_telemetry_history(filter_params)
    return TelemetryHistoryList(total=total, items=items)