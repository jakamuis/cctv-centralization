from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.device import Device, DeviceCreate, DeviceUpdate, DeviceList
from app.services.device import DeviceService
from app.api.v1.dependencies import get_db

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("/", response_model=DeviceList, summary="List devices with filtering and pagination")
async def list_devices(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    site_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    online: Optional[bool] = Query(None),
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    service = DeviceService(db)
    total = await service.count_devices(
        site_id=site_id,
        status=status,
        vendor=vendor,
        online=online,
        include_deleted=include_deleted,
    )
    items = await service.list_devices(
        offset=offset,
        limit=limit,
        site_id=site_id,
        status=status,
        vendor=vendor,
        online=online,
        include_deleted=include_deleted,
    )
    return DeviceList(total=total, items=items)


@router.post("/", response_model=Device, status_code=status.HTTP_201_CREATED, summary="Create a new device")
async def create_device(device_in: DeviceCreate, db: AsyncSession = Depends(get_db)):
    service = DeviceService(db)
    device = await service.create_device(device_in)
    return device


@router.get("/{device_id}", response_model=Device, summary="Get device details by ID")
async def get_device(device_id: str, include_deleted: bool = Query(False), db: AsyncSession = Depends(get_db)):
    service = DeviceService(db)
    device = await service.get_device(device_id, include_deleted=include_deleted)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.put("/{device_id}", response_model=Device, summary="Update device details")
async def update_device(device_id: str, device_in: DeviceUpdate, db: AsyncSession = Depends(get_db)):
    service = DeviceService(db)
    device = await service.get_device(device_id, include_deleted=True)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    updated_device = await service.update_device(device, device_in)
    return updated_device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft delete a device")
async def soft_delete_device(device_id: str, db: AsyncSession = Depends(get_db)):
    service = DeviceService(db)
    device = await service.get_device(device_id, include_deleted=True)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    await service.soft_delete_device(device)
    return None


@router.post("/{device_id}/restore", status_code=status.HTTP_204_NO_CONTENT, summary="Restore a soft-deleted device")
async def restore_device(device_id: str, db: AsyncSession = Depends(get_db)):
    service = DeviceService(db)
    device = await service.get_device(device_id, include_deleted=True)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    await service.restore_device(device)
    return None