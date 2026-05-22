"""
models/nvr_channel.py

SQLAlchemy ORM model for individual camera channels on a discovered NVR.

Why this file exists:
  - Each NVR can have 4–64+ camera channels.  Storing them in a child table
    lets us query "all cameras on NVR X" or "all cameras at site Y" cheaply.
  - Keeps channel data separate from the NVR record so channels can be
    refreshed independently without touching the parent row.

Table: nvr_channels

Key design decisions:
  - `nvr_id` + `channel_id` form a natural unique key per NVR.
  - `channel_id` is a string (not int) because Hikvision uses "1", "2", etc.
    but some firmware returns "101", "201" for sub-streams.
  - `ip_address` is nullable — analog channels have no IP.
  - `protocol` stores the connection type ("HIKVISION", "ONVIF", "ANALOG").
  - `is_enabled` mirrors the NVR's own enable flag for the channel.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class NVRChannel(Base):
    """
    Represents one camera channel (IP or analog) on a DiscoveredNVR.
    """

    __tablename__ = "nvr_channels"

    __table_args__ = (
        # One channel_id per NVR — prevents duplicates on re-sync
        UniqueConstraint(
            "nvr_id", "channel_id",
            name="uq_nvr_channel_nvr_channel_id",
        ),
    )

    # ---- primary key ----

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ---- foreign key ----

    nvr_id = Column(
        UUID(as_uuid=True),
        ForeignKey("discovered_nvrs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ---- channel data (from ISAPI) ----

    channel_id = Column(String(20), nullable=False)       # "1", "2", "101", …
    channel_name = Column(String(255), nullable=True)     # user-defined label
    ip_address = Column(String(45), nullable=True)        # camera IP (IP channels)
    manage_port = Column(Integer, nullable=True)          # camera HTTP port
    protocol = Column(String(50), nullable=True)          # "HIKVISION", "ONVIF", "ANALOG"
    is_enabled = Column(Boolean, nullable=False, default=True)

    # ---- timestamps ----

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # ---- relationships ----

    nvr = relationship(
        "DiscoveredNVR",
        back_populates="channels",
    )

    def __repr__(self) -> str:
        return (
            f"<NVRChannel nvr_id={self.nvr_id} "
            f"ch={self.channel_id!r} "
            f"ip={self.ip_address!r} "
            f"name={self.channel_name!r}>"
        )
