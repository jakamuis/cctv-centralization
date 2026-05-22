from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alerts import Alert
from app.schemas.alerts import AlertFilterParams
from app.repositories.alerts import AlertRepository


class AlertService:
    def __init__(self, session: AsyncSession):
        self.repo = AlertRepository(session)

    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        return await self.repo.get(alert_id)

    async def list_alerts(self, filter_params: AlertFilterParams) -> List[Alert]:
        return await self.repo.list(
            offset=filter_params.offset,
            limit=filter_params.limit,
            device_id=filter_params.device_id,
            site_id=filter_params.site_id,
            alert_type=filter_params.alert_type,
            severity=filter_params.severity,
            status=filter_params.status,
            acknowledged=filter_params.acknowledged,
            start_time=filter_params.start_time,
            end_time=filter_params.end_time,
        )

    async def count_alerts(self, filter_params: AlertFilterParams) -> int:
        return await self.repo.count(
            device_id=filter_params.device_id,
            site_id=filter_params.site_id,
            alert_type=filter_params.alert_type,
            severity=filter_params.severity,
            status=filter_params.status,
            acknowledged=filter_params.acknowledged,
            start_time=filter_params.start_time,
            end_time=filter_params.end_time,
        )

    async def acknowledge_alert(self, alert: Alert) -> Alert:
        return await self.repo.acknowledge(alert)

    async def resolve_alert(self, alert: Alert) -> Alert:
        return await self.repo.resolve(alert)