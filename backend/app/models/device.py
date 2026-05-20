from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, DateTime, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import UUIDMixin, TimestampMixin

class Device(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)
    device_name = Column(String(100), nullable=False)
    device_type = Column(String(50), nullable=False)
    vendor = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=False, index=True)
    port = Column(Integer, nullable=False)
    username = Column(String(50), nullable=False)
    password_encrypted = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen = Column(DateTime, nullable=True)

    branch = relationship("Branch", back_populates="devices")
    cameras = relationship("Camera", back_populates="device", cascade="all, delete-orphan")

Index("ix_devices_ip_address", Device.ip_address)