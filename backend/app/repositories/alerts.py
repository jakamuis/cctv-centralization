from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from app.models.alerts import Alert
from app.models.device import Device


class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, alert_id: str) -> Optional[Alert]:
        result = await self.session.execute(select(Alert).where(Alert.id == alert_id))
        return result.scalars().first()

    async def list(
        self,
        offset: int = 0,
        limit: int = 100,
        device_id: Optional[str] = None,
        site_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[Alert]:
        query = select(Alert).join(Device)

        filters = []
        if device_id:
            filters.append(Alert.device_id == device_id)
        if site_id:
            filters.append(Device.site_id == site_id)
        if alert_type:
            filters.append(Alert.alert_type == alert_type)
        if severity:
            filters.append(Alert.severity == severity)
        if status is not None:
            if status == "active":
                filters.append(Alert.active == True)
            elif status == "resolved":
                filters.append(Alert.active == False)
        if acknowledged is not None:
            filters.append(Alert.acknowledged == acknowledged)
        if start_time:
            filters.append(Alert.created_at >= start_time)
        if end_time:
            filters.append(Alert.created_at <= end_time)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(desc(Alert.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(
        self,
        device_id: Optional[str] = None,
        site_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> int:
        query = select(Alert).join(Device)

        filters = []
        if device_id:
            filters.append(Alert.device_id == device_id)
        if site_id:
            filters.append(Device.site_id == site_id)
        if alert_type:
            filters.append(Alert.alert_type == alert_type)
        if severity:
            filters.append(Alert.severity == severity)
        if status is not None:
            if status == "active":
                filters.append(Alert.active == True)
            elif status == "resolved":
                filters.append(Alert.active == False)
        if acknowledged is not None:
            filters.append(Alert.acknowledged == acknowledged)
        if start_time:
            filters.append(Alert.created_at >= start_time)
        if end_time:
            filters.append(Alert.created_at <= end_time)

        if filters:
            query = query.where(and_(*filters))

        result = await self.session.execute(query)
        return len(result.scalars().all())

    async def acknowledge(self, alert: Alert) -> Alert:
        if alert.acknowledged:
            return alert
        alert.acknowledged = True
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def resolve(self, alert: Alert) -> Alert:
        if not alert.active:
            return alert
        from datetime import datetime
        alert.active = False
        alert.resolved_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(alert)
        return alert