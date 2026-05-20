from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import UUIDMixin, TimestampMixin

class Camera(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cameras"

    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    channel_number = Column(Integer, nullable=False)
    camera_name = Column(String(100), nullable=False)
    stream_path = Column(String(255), nullable=True)
    is_recording = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    device = relationship("Device", back_populates="cameras")

Index("ix_cameras_device_channel", Camera.device_id, Camera.channel_number, unique=True)