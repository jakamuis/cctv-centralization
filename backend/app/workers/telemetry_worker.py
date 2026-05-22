import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import async_session_maker
from app.models.device import Device, DeviceStatusEnum
from app.models.current_device_state import CurrentDeviceState
from app.models.telemetry_history import TelemetryHistory
from app.models.alerts import Alert, AlertSeverityEnum, AlertTypeEnum
from app.services.alerts import AlertService
from app.hikvision.client import HikvisionClient
from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("telemetry_worker")

MAX_CONCURRENT_REQUESTS = 20

class TelemetryWorker:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.hikvision_client = HikvisionClient()
        self.alert_service = None  # Will be initialized with DB session

    async def poll_device(self, device: Device, session: AsyncSession):
        async with self.semaphore:
            try:
                # Poll device info from Hikvision ISAPI
                device_info = await self.hikvision_client.get_device_info(device)
                storage_info = await self.hikvision_client.get_storage_info(device)
                stream_info = await self.hikvision_client.get_stream_info(device)
                recording_info = await self.hikvision_client.get_recording_info(device)

                # Update current device state
                current_state = await session.get(CurrentDeviceState, device.id)
                if not current_state:
                    current_state = CurrentDeviceState(device_id=device.id)
                current_state.online_status = DeviceStatusEnum.ONLINE.value
                current_state.storage_usage = storage_info.usage if storage_info else None
                current_state.recording_ok = recording_info.ok if recording_info else None
                current_state.stream_ok = stream_info.ok if stream_info else None
                current_state.cpu_usage = device_info.cpu_usage if device_info else None
                current_state.memory_usage = device_info.memory_usage if device_info else None
                current_state.temperature = device_info.temperature if device_info else None
                current_state.health_score = self.calculate_health_score(current_state)
                current_state.updated_at = datetime.utcnow()

                session.add(current_state)

                # Append telemetry history
                await self.append_telemetry_history(session, device, device_info, storage_info, stream_info, recording_info)

                # Generate alerts based on state changes
                await self.generate_alerts(session, device, current_state)

                await session.commit()
                logger.info(f"Polled device {device.id} successfully")
            except Exception as e:
                logger.error(f"Error polling device {device.id}: {e}")
                await session.rollback()

    async def append_telemetry_history(self, session: AsyncSession, device: Device, device_info, storage_info, stream_info, recording_info):
        # Append relevant telemetry metrics to history table
        now = datetime.utcnow()
        metrics = []
        if device_info:
            metrics.append(TelemetryHistory(device_id=device.id, metric="cpu_usage", value=device_info.cpu_usage, timestamp=now))
            metrics.append(TelemetryHistory(device_id=device.id, metric="memory_usage", value=device_info.memory_usage, timestamp=now))
            metrics.append(TelemetryHistory(device_id=device.id, metric="temperature", value=device_info.temperature, timestamp=now))
        if storage_info:
            metrics.append(TelemetryHistory(device_id=device.id, metric="storage_usage", value=storage_info.usage, timestamp=now))
        if stream_info:
            metrics.append(TelemetryHistory(device_id=device.id, metric="stream_ok", value=1.0 if stream_info.ok else 0.0, timestamp=now))
        if recording_info:
            metrics.append(TelemetryHistory(device_id=device.id, metric="recording_ok", value=1.0 if recording_info.ok else 0.0, timestamp=now))

        session.add_all(metrics)

    async def generate_alerts(self, session: AsyncSession, device: Device, current_state: CurrentDeviceState):
        # Implement alert generation logic with debounce and cooldown
        # Example: generate offline alert if device offline threshold exceeded
        pass

    def calculate_health_score(self, current_state: CurrentDeviceState) -> float:
        # Calculate health score based on metrics
        return 100.0  # Placeholder

    async def run(self):
        while True:
            async with async_session_maker() as session:
                self.alert_service = AlertService(session)
                devices = await session.execute(select(Device).where(Device.is_deleted == False))
                devices_list = devices.scalars().all()
                tasks = [self.poll_device(device, session) for device in devices_list]
                await asyncio.gather(*tasks)
            await asyncio.sleep(settings.telemetry.polling_interval_seconds or 30)