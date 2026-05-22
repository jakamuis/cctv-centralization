from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class AlertBase(BaseModel):
    device_id: UUID
    alert_type: str
    severity: str
    message: str
    active: bool = True
    acknowledged: bool = False
    resolved_at: Optional[datetime] = None
    created_at: datetime


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    acknowledged: Optional[bool] = None
    active: Optional[bool] = None
    resolved_at: Optional[datetime] = None


class Alert(AlertBase):
    id: UUID

    class Config:
        from_attributes = True


class AlertList(BaseModel):
    total: int
    items: List[Alert]


class AlertFilterParams(BaseModel):
    device_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    acknowledged: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)