from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.schemas.camera import Camera, CameraList
from app.services.camera import CameraService
from app.api.v1.dependencies import get_db

router = APIRouter()

@router.get("/cameras", response_model=CameraList)
async def list_cameras(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    branch_id: Optional[UUID] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    service = CameraService(db)
    filters = {}
    if branch_id:
        filters["branch_id"] = branch_id
    if enabled is not None:
        filters["enabled"] = enabled
    result = await service.repo.list(skip=skip, limit=limit, **filters)
    return CameraList(total=result["total"], items=result["items"])

@router.get("/cameras/{camera_id}", response_model=Camera)
async def get_camera(
    camera_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = CameraService(db)
    camera = await service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@router.get("/branches/{branch_id}/cameras", response_model=CameraList)
async def list_cameras_by_branch(
    branch_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    enabled: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    service = CameraService(db)
    filters = {"branch_id": branch_id}
    if enabled is not None:
        filters["enabled"] = enabled
    result = await service.repo.list(skip=skip, limit=limit, **filters)
    return CameraList(total=result["total"], items=result["items"])