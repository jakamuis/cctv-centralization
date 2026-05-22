from sqlalchemy import Column, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, UUIDMixin
import enum


class OnlineStatusEnum(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
    MAINTENANCE = "MAINTENANCE"


class CurrentDeviceState(UUIDMixin, Base):
    __tablename__ = "current_device_state"

    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), unique=True, nullable=False, index=True)
    online_status = Column(Enum(OnlineStatusEnum), nullable=False, default=OnlineStatusEnum.UNKNOWN)
    storage_usage = Column(Float, nullable=True)  # percentage or GB depending on implementation
    recording_ok = Column(Boolean, nullable=True)
    stream_ok = Column(Boolean, nullable=True)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    health_score = Column(Float, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    device = relationship("Device", back_populates="current_state", uselist=False)