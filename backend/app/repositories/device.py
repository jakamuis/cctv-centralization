# backend/app/repositories/device.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device


class DeviceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload):

        if isinstance(payload, Device):

            self.db.add(payload)

            await self.db.commit()

            await self.db.refresh(payload)

            return payload

        if hasattr(payload, "model_dump"):
            data = payload.model_dump()
        else:
            data = {
                k: v
                for k, v in payload.__dict__.items()
                if not k.startswith("_")
            }

        device = Device(**data)

        self.db.add(device)

        await self.db.commit()

        await self.db.refresh(device)

        return device

    async def get(
        self,
        device_id,
        include_deleted: bool = False
    ):

        query = select(Device).where(
            Device.id == device_id
        )

        if not include_deleted and hasattr(Device, "is_deleted"):
            query = query.where(
                Device.is_deleted == False
            )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_by_id(self, device_id: UUID):

        query = select(Device).where(Device.id == device_id)
        if hasattr(Device, "is_deleted"):
            query = query.where(Device.is_deleted == False)
        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        offset: Optional[int] = None,
        limit: int = 100,
        site_id: Optional[UUID] = None,
        status: Optional[str] = None,
        vendor: Optional[str] = None,
        online: Optional[bool] = None,
        include_deleted: bool = False,
    ):
        if offset is not None:
            skip = offset

        query = select(Device)

        if not include_deleted and hasattr(Device, "is_deleted"):
            query = query.where(Device.is_deleted == False)

        if site_id:
            query = query.where(Device.site_id == site_id)

        if status:
            query = query.where(Device.status == status)

        if vendor:
            query = query.where(Device.vendor == vendor)

        if online is not None:
            query = query.where(
                Device.status == ("ONLINE" if online else "OFFLINE")
            )

        total_query = select(func.count()).select_from(
            query.subquery()
        )

        total_result = await self.db.execute(total_query)

        total = total_result.scalar()

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)

        items = result.scalars().all()

        return {
            "total": total,
            "items": items,
        }

    async def count(
        self,
        site_id: Optional[UUID] = None,
        status: Optional[str] = None,
        vendor: Optional[str] = None,
        online: Optional[bool] = None,
        include_deleted: bool = False,
    ) -> int:
        result = await self.list(
            skip=0,
            limit=1,
            site_id=site_id,
            status=status,
            vendor=vendor,
            online=online,
            include_deleted=include_deleted,
        )
        return result["total"]

    async def update(self, device, payload):

        if hasattr(payload, "model_dump"):
            data = payload.model_dump(exclude_unset=True)
        else:
            data = {
                k: v
                for k, v in payload.__dict__.items()
                if not k.startswith("_")
            }

        for key, value in data.items():
            setattr(device, key, value)

        device.updated_at = datetime.utcnow()

        await self.db.commit()

        await self.db.refresh(device)

        return device

    async def soft_delete(self, device):
        if not hasattr(device, "is_deleted"):
            await self.db.delete(device)
            await self.db.commit()
            return device

        device.is_deleted = True

        device.deleted_at = datetime.utcnow()

        device.updated_at = datetime.utcnow()

        await self.db.commit()

        await self.db.refresh(device)

        return device

    async def restore(self, device):
        if not hasattr(device, "is_deleted"):
            return device

        device.is_deleted = False

        device.deleted_at = None

        device.updated_at = datetime.utcnow()

        await self.db.commit()

        await self.db.refresh(device)

        return device
