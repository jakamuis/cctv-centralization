from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from app.models.telemetry_history import TelemetryHistory
from app.models.current_device_state import CurrentDeviceState
from app.models.device import Device


class TelemetryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_device_state(self, device_id: str) -> Optional[CurrentDeviceState]:
        result = await self.session.execute(
            select(CurrentDeviceState).where(CurrentDeviceState.device_id == device_id)
        )
        return result.scalars().first()

    async def list_telemetry_history(
        self,
        offset: int = 0,
        limit: int = 100,
        device_id: Optional[str] = None,
        site_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[TelemetryHistory]:
        query = select(TelemetryHistory).join(Device, TelemetryHistory.device_id == Device.id)

        filters = []
        if device_id:
            filters.append(TelemetryHistory.device_id == device_id)
        if site_id:
            filters.append(Device.site_id == site_id)
        if status:
            filters.append(Device.status == status)
        if start_time:
            filters.append(TelemetryHistory.timestamp >= start_time)
        if end_time:
            filters.append(TelemetryHistory.timestamp <= end_time)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(desc(TelemetryHistory.timestamp)).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_telemetry_history(
        self,
        device_id: Optional[str] = None,
        site_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> int:
        query = select(TelemetryHistory).join(Device, TelemetryHistory.device_id == Device.id)

        filters = []
        if device_id:
            filters.append(TelemetryHistory.device_id == device_id)
        if site_id:
            filters.append(Device.site_id == site_id)
        if status:
            filters.append(Device.status == status)
        if start_time:
            filters.append(TelemetryHistory.timestamp >= start_time)
        if end_time:
            filters.append(TelemetryHistory.timestamp <= end_time)

        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        return len(result.scalars().all())