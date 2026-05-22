from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class DeviceBase(BaseModel):
    site_id: UUID
    device_type: str = Field(..., max_length=50)
    vendor: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    firmware_version: Optional[str] = Field(None, max_length=50)
    ip_address: Optional[str] = Field(None, max_length=45)
    port: Optional[int] = None
    username: Optional[str] = Field(None, max_length=100)
    mac_address: Optional[str] = Field(None, max_length=17)
    status: str = Field(..., max_length=50)
    heartbeat_interval_seconds: int = 30
    offline_threshold_seconds: int = 120


class DeviceCreate(DeviceBase):
    encrypted_password: Optional[str] = None


class DeviceUpdate(BaseModel):
    site_id: Optional[UUID] = None
    device_type: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    encrypted_password: Optional[str] = None
    mac_address: Optional[str] = None
    status: Optional[str] = None
    heartbeat_interval_seconds: Optional[int] = None
    offline_threshold_seconds: Optional[int] = None
    is_deleted: Optional[bool] = None


class DeviceInDBBase(DeviceBase):
    id: UUID
    last_seen_at: Optional[datetime] = None
    last_online_at: Optional[datetime] = None
    last_offline_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Device(DeviceInDBBase):
    pass


class DeviceList(BaseModel):
    total: int
    items: list[Device]