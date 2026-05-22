from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.current_device_state import CurrentDeviceState
from app.models.telemetry_history import TelemetryHistory
from app.schemas.telemetry import TelemetryFilterParams
from app.repositories.telemetry import TelemetryRepository


class TelemetryService:
    def __init__(self, session: AsyncSession):
        self.repo = TelemetryRepository(session)

    async def get_latest_device_state(self, device_id: str) -> Optional[CurrentDeviceState]:
        return await self.repo.get_latest_device_state(device_id)

    async def list_telemetry_history(
        self,
        filter_params: TelemetryFilterParams,
    ) -> List[TelemetryHistory]:
        return await self.repo.list_telemetry_history(
            offset=filter_params.offset,
            limit=filter_params.limit,
            device_id=filter_params.device_id,
            site_id=filter_params.site_id,
            status=filter_params.status,
            start_time=filter_params.start_time,
            end_time=filter_params.end_time,
        )

    async def count_telemetry_history(
        self,
        filter_params: TelemetryFilterParams,
    ) -> int:
        return await self.repo.count_telemetry_history(
            device_id=filter_params.device_id,
            site_id=filter_params.site_id,
            status=filter_params.status,
            start_time=filter_params.start_time,
            end_time=filter_params.end_time,
        )