from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.repositories.device import DeviceRepository


class DeviceService:
    def __init__(self, session: AsyncSession):
        self.repo = DeviceRepository(session)

    async def get_device(self, device_id: str, include_deleted: bool = False) -> Optional[Device]:
        return await self.repo.get(device_id, include_deleted=include_deleted)

    async def list_devices(
        self,
        offset: int = 0,
        limit: int = 100,
        site_id: Optional[str] = None,
        status: Optional[str] = None,
        vendor: Optional[str] = None,
        online: Optional[bool] = None,
        include_deleted: bool = False,
    ) -> List[Device]:
        return await self.repo.list(
            offset=offset,
            limit=limit,
            site_id=site_id,
            status=status,
            vendor=vendor,
            online=online,
            include_deleted=include_deleted,
        )

    async def count_devices(
        self,
        site_id: Optional[str] = None,
        status: Optional[str] = None,
        vendor: Optional[str] = None,
        online: Optional[bool] = None,
        include_deleted: bool = False,
    ) -> int:
        return await self.repo.count(
            site_id=site_id,
            status=status,
            vendor=vendor,
            online=online,
            include_deleted=include_deleted,
        )

    async def create_device(self, device_in: DeviceCreate) -> Device:
        device = Device(**device_in.model_dump())
        return await self.repo.create(device)

    async def update_device(self, device: Device, device_in: DeviceUpdate) -> Device:
        for field, value in device_in.model_dump(exclude_unset=True).items():
            setattr(device, field, value)
        return await self.repo.update(device)

    async def soft_delete_device(self, device: Device) -> None:
        await self.repo.soft_delete(device)

    async def restore_device(self, device: Device) -> None:
        await self.repo.restore(device)