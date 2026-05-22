from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SiteBase(BaseModel):
    code: str
    name: str
    address: Optional[str] = None
    timezone: str
    region: Optional[str] = None


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
    region: Optional[str] = None


class Site(SiteBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SiteList(BaseModel):
    items: list[Site]
    total: int