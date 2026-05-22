from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CurrentDeviceStateBase(BaseModel):
    device_id: UUID
    online_status: str
    storage_usage: Optional[float] = None
    recording_ok: Optional[bool] = None
    stream_ok: Optional[bool] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    temperature: Optional[float] = None
    health_score: Optional[float] = None
    updated_at: datetime


class CurrentDeviceState(CurrentDeviceStateBase):
    class Config:
        from_attributes = True


class TelemetryHistoryBase(BaseModel):
    device_id: UUID
    metric: str
    value: float
    timestamp: datetime


class TelemetryHistory(TelemetryHistoryBase):
    class Config:
        from_attributes = True


class TelemetryHistoryList(BaseModel):
    total: int
    items: List[TelemetryHistory]


class TelemetryFilterParams(BaseModel):
    device_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)