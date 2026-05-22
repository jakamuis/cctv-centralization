from sqlalchemy import Column, DateTime, Integer, Enum, ForeignKey
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, UUIDMixin
import enum


class StreamSessionStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    FAILED = "FAILED"


class StreamSession(UUIDMixin, Base):
    __tablename__ = "stream_sessions"

    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    viewer_count = Column(Integer, default=0, nullable=False)
    status = Column(Enum(StreamSessionStatusEnum), default=StreamSessionStatusEnum.ACTIVE, nullable=False)