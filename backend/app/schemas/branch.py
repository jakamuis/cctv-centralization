from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class BranchBase(BaseModel):
    name: str
    code: str
    location: Optional[str] = None


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    location: Optional[str] = None


class BranchInDBBase(BranchBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Branch(BranchInDBBase):
    pass


class BranchList(BaseModel):
    total: int
    items: list[Branch]