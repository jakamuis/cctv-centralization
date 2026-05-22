from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class CameraBase(BaseModel):
    branch_id: UUID
    name: str = Field(..., max_length=255)
    stream_name: str = Field(..., max_length=255)
    rtsp_channel: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)
    enabled: bool = True


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    branch_id: Optional[UUID] = None
    name: Optional[str] = None
    stream_name: Optional[str] = None
    rtsp_channel: Optional[str] = None
    status: Optional[str] = None
    enabled: Optional[bool] = None


class CameraInDBBase(CameraBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Camera(CameraInDBBase):
    pass


class CameraList(BaseModel):
    total: int
    items: list[Camera]