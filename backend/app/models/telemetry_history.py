from sqlalchemy import Column, DateTime, Float, String, ForeignKey, Index
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, UUIDMixin


class TelemetryHistory(UUIDMixin, Base):
    __tablename__ = "telemetry_history"

    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    metric = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)


Index("ix_telemetry_history_timestamp", TelemetryHistory.timestamp)