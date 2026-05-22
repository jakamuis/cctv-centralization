from sqlalchemy import Column, String, Integer, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, UUIDMixin, TimestampMixin


class DeviceTypeEnum(str, enum.Enum):
    NVR = "NVR"
    CAMERA = "CAMERA"
    ENCODER = "ENCODER"
    DECODER = "DECODER"
    SWITCH = "SWITCH"
    SERVER = "SERVER"


class DeviceStatusEnum(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
    MAINTENANCE = "MAINTENANCE"


class Device(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=False,
        index=True
    )

    device_type = Column(
        Enum(DeviceTypeEnum),
        nullable=False,
        index=True
    )

    vendor = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)

    serial_number = Column(
        String(100),
        nullable=True,
        unique=True
    )

    firmware_version = Column(String(50), nullable=True)

    ip_address = Column(String(45), nullable=True)

    port = Column(Integer, nullable=True)

    username = Column(String(100), nullable=True)

    encrypted_password = Column(String(255), nullable=True)

    mac_address = Column(String(17), nullable=True)

    status = Column(
        Enum(DeviceStatusEnum),
        nullable=False,
        default=DeviceStatusEnum.UNKNOWN,
        index=True
    )

    heartbeat_interval_seconds = Column(
        Integer,
        nullable=False,
        default=30
    )

    offline_threshold_seconds = Column(
        Integer,
        nullable=False,
        default=120
    )

    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    last_online_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    last_offline_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=datetime.utcnow
    )

    # RELATIONSHIPS

    site = relationship(
        "Site",
        back_populates="devices"
    )

    # Removed legacy cameras relationship to fix import script errors
    # cameras = relationship(
    #     "Camera",
    #     back_populates="device",
    #     cascade="all, delete-orphan"
    # )

    current_state = relationship(
        "CurrentDeviceState",
        back_populates="device",
        uselist=False
    )