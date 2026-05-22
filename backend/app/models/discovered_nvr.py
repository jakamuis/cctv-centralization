"""
models/discovered_nvr.py

SQLAlchemy ORM model for NVR devices discovered via the Google Sheet CSV sync.

Why this file exists:
  - Stores the canonical record of each NVR that has been successfully synced.
  - Keeps discovery data separate from the generic `devices` table so the
    discovery pipeline can evolve independently.
  - Acts as the parent for NVRChannel rows (one NVR → many channels).

Table: discovered_nvrs

Key design decisions:
  - `site_code` + `nvr_ip` + `http_port` form a natural unique key.
    If the same NVR is re-synced, the row is updated (upsert), not duplicated.
  - Credentials are stored as-is for now (plain text).  In a later phase
    these should be encrypted at rest using a KMS or Fernet key.
  - `last_synced_at` is updated on every successful sync so operators can
    see when data was last refreshed.
  - `sync_status` records the outcome of the most recent sync attempt so
    the UI can show a health indicator without re-querying the device.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class DiscoveredNVR(Base):
    """
    Represents one NVR row from the Google Sheet CSV after a successful sync.
    """

    __tablename__ = "discovered_nvrs"

    __table_args__ = (
        # Prevent duplicate rows for the same physical device
        UniqueConstraint(
            "site_code", "nvr_ip", "http_port",
            name="uq_discovered_nvr_site_ip_port",
        ),
    )

    # ---- primary key ----

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ---- seed data (from CSV) ----

    site_code = Column(String(100), nullable=False, index=True)
    branch_name = Column(String(255), nullable=True)
    nvr_ip = Column(String(45), nullable=False, index=True)
    http_port = Column(Integer, nullable=False, default=80)
    rtsp_port = Column(Integer, nullable=False, default=554)

    # Credentials — stored for re-use during subsequent syncs / stream pulls.
    # TODO Phase 8: encrypt these with Fernet before storing.
    username = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)

    # ---- device info (from ISAPI) ----

    device_name = Column(String(255), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, index=True)
    mac_address = Column(String(17), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    device_type = Column(String(50), nullable=True)   # "NVR", "DVR", etc.

    # ---- sync metadata ----

    # "synced" | "failed" | "auth_error" | "unreachable"
    sync_status = Column(String(50), nullable=False, default="synced")
    sync_error = Column(String(500), nullable=True)   # last error message
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

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

    channels = relationship(
        "NVRChannel",
        back_populates="nvr",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<DiscoveredNVR site={self.site_code!r} "
            f"ip={self.nvr_ip!r} port={self.http_port} "
            f"status={self.sync_status!r}>"
        )
