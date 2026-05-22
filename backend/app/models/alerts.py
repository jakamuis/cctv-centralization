from sqlalchemy import Column, DateTime, String, Boolean, Enum, ForeignKey
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, UUIDMixin
import enum


class AlertSeverityEnum(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertTypeEnum(str, enum.Enum):
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    DEVICE_ONLINE = "DEVICE_ONLINE"
    STORAGE_WARNING = "STORAGE_WARNING"
    RECORDING_FAILURE = "RECORDING_FAILURE"
    STREAM_DOWN = "STREAM_DOWN"
    DEVICE_FLAPPING = "DEVICE_FLAPPING"
    # Add other alert types as needed


class Alert(UUIDMixin, Base):
    __tablename__ = "alerts"

    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    alert_type = Column(Enum(AlertTypeEnum), nullable=False)
    severity = Column(Enum(AlertSeverityEnum), nullable=False)
    message = Column(String(500), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)