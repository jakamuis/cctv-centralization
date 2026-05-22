import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.device import Device, DeviceStatusEnum
from app.models.alerts import Alert, AlertSeverityEnum, AlertTypeEnum
from app.services.alerts import AlertService
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("alert_generation")

class AlertGenerationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.alert_service = AlertService(session)
        self.offline_threshold = settings.telemetry.offline_threshold_seconds or 120
        self.alert_cooldown_seconds = settings.telemetry.alert_cooldown_seconds or 300
        self.device_flap_threshold = 5
        self.device_flap_window_seconds = 600  # 10 minutes

    async def process_device_state(self, device: Device, current_state):
        now = datetime.utcnow()
        offline_duration = (now - device.last_seen_at).total_seconds() if device.last_seen_at else None

        # Check offline condition
        if offline_duration and offline_duration > self.offline_threshold:
            await self._handle_offline_alert(device, offline_duration)
        else:
            await self._handle_online_recovery(device)

        # TODO: Implement stream failure, storage issues, and flapping detection

    async def _handle_offline_alert(self, device: Device, offline_duration: float):
        # Check for existing active offline alert
        existing_alert = await self._get_active_alert(device.id, AlertTypeEnum.DEVICE_OFFLINE)
        if existing_alert:
            # Check cooldown
            if (datetime.utcnow() - existing_alert.created_at).total_seconds() < self.alert_cooldown_seconds:
                logger.debug(f"Cooldown active for offline alert on device {device.id}")
                return
        else:
            # Create new offline alert
            message = f"Device {device.id} is offline for {offline_duration} seconds."
            await self._create_alert(device.id, AlertTypeEnum.DEVICE_OFFLINE, AlertSeverityEnum.CRITICAL, message)
            logger.info(f"Created offline alert for device {device.id}")

    async def _handle_online_recovery(self, device: Device):
        # Check for existing active offline alert
        existing_alert = await self._get_active_alert(device.id, AlertTypeEnum.DEVICE_OFFLINE)
        if existing_alert:
            # Resolve offline alert
            await self.alert_service.resolve_alert(existing_alert)
            # Create recovery alert
            message = f"Device {device.id} has recovered and is online."
            await self._create_alert(device.id, AlertTypeEnum.DEVICE_ONLINE, AlertSeverityEnum.INFO, message)
            logger.info(f"Device {device.id} recovered, offline alert resolved")

    async def _get_active_alert(self, device_id: str, alert_type: AlertTypeEnum) -> Optional[Alert]:
        alerts = await self.alert_service.list_alerts(
            filter_params=AlertFilterParams(
                device_id=device_id,
                alert_type=alert_type,
                status="active",
                limit=1,
                offset=0,
            )
        )
        return alerts[0] if alerts else None

    async def _create_alert(self, device_id: str, alert_type: AlertTypeEnum, severity: AlertSeverityEnum, message: str):
        alert = Alert(
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            active=True,
            acknowledged=False,
            created_at=datetime.utcnow(),
        )
        await self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        # TODO: Publish alert event to Redis pub/sub