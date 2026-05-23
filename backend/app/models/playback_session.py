"""
models/playback_session.py

SQLAlchemy ORM model for playback sessions.

Each row represents one active (or recently expired) playback session.
A session ties a user request to a temporary go2rtc stream that replays
a Hikvision recording segment.

Lifecycle:
  CREATE  → go2rtc stream registered, frontend starts playing
  ACTIVE  → frontend consuming the stream
  EXPIRED → idle timeout or explicit close; go2rtc stream removed
  CLOSED  → manually closed by user or cleanup worker
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class PlaybackSession(Base):
    """
    Represents one playback session for a recorded segment.

    stream_name is the temporary go2rtc stream key, e.g.:
        playback_<nvr_id_short>_ch<channel>_<timestamp>
    """

    __tablename__ = "playback_sessions"

    # ---- primary key ----

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ---- session data ----

    # UUID of the DiscoveredNVR that owns this recording
    device_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # NVR channel number (1-based, matches Hikvision track numbering)
    channel = Column(Integer, nullable=False)

    # Requested recording window
    start_time = Column(DateTime(timezone=False), nullable=False)
    end_time = Column(DateTime(timezone=False), nullable=False)

    # Temporary go2rtc stream name — unique per session
    stream_name = Column(String(255), nullable=False, unique=True)

    # ---- lifecycle timestamps ----

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # When this session should be auto-expired by the cleanup worker
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # ---- audit ----

    # Integer FK to users.id (nullable — system-initiated sessions have no user)
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PlaybackSession id={self.id} "
            f"device={self.device_id} ch={self.channel} "
            f"stream={self.stream_name!r}>"
        )
