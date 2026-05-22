from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, UUIDMixin, TimestampMixin


class Site(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sites"

    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    timezone = Column(String(50), nullable=False)
    region = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    devices = relationship("Device", back_populates="site", cascade="all, delete-orphan")