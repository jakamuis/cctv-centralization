from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.camera import Camera, CameraCreate, CameraUpdate, CameraList
from app.services.camera import CameraService
from app.api.v1.dependencies import get_db

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("/", response_model=CameraList, summary="List cameras with filtering and pagination")
async def list_cameras(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    device_id: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    status: Optional[str] = Query(None),
    ptz_enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = CameraService(db)
    total = await service.count_cameras(
        device_id=device_id,
        site_id=site_id,
        enabled=enabled,
        status=status,
        ptz_enabled=ptz_enabled,
    )
    items = await service.list_cameras(
        offset=offset,
        limit=limit,
        device_id=device_id,
        site_id=site_id,
        enabled=enabled,
        status=status,
        ptz_enabled=ptz_enabled,
    )
    return CameraList(total=total, items=items)


@router.post("/", response_model=Camera, status_code=status.HTTP_201_CREATED, summary="Create a new camera")
async def create_camera(camera_in: CameraCreate, db: AsyncSession = Depends(get_db)):
    service = CameraService(db)
    camera = await service.create_camera(camera_in)
    return camera


@router.get("/{camera_id}", response_model=Camera, summary="Get camera details by ID")
async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


@router.put("/{camera_id}", response_model=Camera, summary="Update camera details")
async def update_camera(camera_id: str, camera_in: CameraUpdate, db: AsyncSession = Depends(get_db)):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    updated_camera = await service.update_camera(camera, camera_in)
    return updated_camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Disable (soft delete) a camera")
async def soft_delete_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    await service.soft_delete_camera(camera)
    return None


@router.post("/{camera_id}/restore", status_code=status.HTTP_204_NO_CONTENT, summary="Restore a disabled camera")
async def restore_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    await service.restore_camera(camera)
    return None