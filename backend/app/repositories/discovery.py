"""
repositories/discovery.py

Database access layer for the discovery pipeline.

Why this file exists:
  - Keeps all SQL/ORM logic out of the sync engine and API router.
  - Provides upsert semantics: re-syncing the same NVR updates the existing
    row rather than inserting a duplicate.
  - Channel upsert deletes stale channels (ones that disappeared from the NVR)
    and inserts/updates the current set atomically within a transaction.

Design decisions:
  - Uses SQLAlchemy Core `insert(...).on_conflict_do_update` (PostgreSQL
    dialect) for true upserts — avoids the SELECT-then-INSERT race condition.
  - All methods accept an AsyncSession injected by the caller (FastAPI
    dependency injection) so the session lifecycle is managed externally.
  - No commits inside the repository — the service layer commits after all
    operations for a device succeed, so a partial failure rolls back cleanly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discovered_nvr import DiscoveredNVR
from app.models.nvr_channel import NVRChannel
from app.discovery.schemas import HikvisionDeviceInfo, HikvisionChannel

logger = logging.getLogger(__name__)


class DiscoveryRepository:
    """
    Async repository for DiscoveredNVR and NVRChannel persistence.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # DiscoveredNVR
    # ------------------------------------------------------------------

    async def upsert_nvr(
        self,
        *,
        site_code: str,
        branch_name: Optional[str],
        nvr_ip: str,
        http_port: int,
        rtsp_port: int,
        username: str,
        password: str,
        device_info: Optional[HikvisionDeviceInfo],
        sync_status: str,
        sync_error: Optional[str] = None,
    ) -> DiscoveredNVR:
        """
        Insert or update a DiscoveredNVR row.

        The unique constraint on (site_code, nvr_ip, http_port) is used as
        the conflict target.  On conflict every mutable column is refreshed
        so the row always reflects the latest sync.

        Returns the persisted DiscoveredNVR ORM object (not yet committed).
        """

        now = datetime.now(tz=timezone.utc)

        values: dict = {
            "site_code": site_code,
            "branch_name": branch_name,
            "nvr_ip": nvr_ip,
            "http_port": http_port,
            "rtsp_port": rtsp_port,
            "username": username,
            "password": password,
            "sync_status": sync_status,
            "sync_error": sync_error,
            "last_synced_at": now,
        }

        if device_info:
            values.update(
                {
                    "device_name": device_info.device_name,
                    "model": device_info.model,
                    "serial_number": device_info.serial_number,
                    "mac_address": device_info.mac_address,
                    "firmware_version": device_info.firmware_version,
                    "device_type": device_info.device_type,
                }
            )

        # PostgreSQL upsert — insert or update on conflict
        stmt = (
            pg_insert(DiscoveredNVR)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_discovered_nvr_site_ip_port",
                set_={
                    k: v
                    for k, v in values.items()
                    # Don't overwrite the primary key or created_at
                    if k not in ("site_code", "nvr_ip", "http_port")
                },
            )
            .returning(DiscoveredNVR.id)
        )

        result = await self.db.execute(stmt)
        nvr_id: UUID = result.scalar_one()

        logger.debug(
            "Upserted DiscoveredNVR id=%s site=%s ip=%s status=%s",
            nvr_id, site_code, nvr_ip, sync_status,
        )

        # Re-fetch the full ORM object so the caller has a proper instance
        nvr = await self.get_nvr_by_id(nvr_id)
        return nvr  # type: ignore[return-value]

    async def get_nvr_by_id(self, nvr_id: UUID) -> Optional[DiscoveredNVR]:
        """Fetch a single DiscoveredNVR by primary key."""
        result = await self.db.execute(
            select(DiscoveredNVR).where(DiscoveredNVR.id == nvr_id)
        )
        return result.scalar_one_or_none()

    async def get_nvr_by_ip(
        self, site_code: str, nvr_ip: str, http_port: int
    ) -> Optional[DiscoveredNVR]:
        """Fetch a DiscoveredNVR by its natural key."""
        result = await self.db.execute(
            select(DiscoveredNVR).where(
                DiscoveredNVR.site_code == site_code,
                DiscoveredNVR.nvr_ip == nvr_ip,
                DiscoveredNVR.http_port == http_port,
            )
        )
        return result.scalar_one_or_none()

    async def list_nvrs(
        self,
        site_code: Optional[str] = None,
        sync_status: Optional[str] = None,
        offset: int = 0,
        limit: int = 200,
    ) -> List[DiscoveredNVR]:
        """List DiscoveredNVR rows with optional filters."""
        query = select(DiscoveredNVR)
        if site_code:
            query = query.where(DiscoveredNVR.site_code == site_code)
        if sync_status:
            query = query.where(DiscoveredNVR.sync_status == sync_status)
        query = query.order_by(DiscoveredNVR.site_code, DiscoveredNVR.nvr_ip)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # NVRChannel
    # ------------------------------------------------------------------

    async def replace_channels(
        self,
        nvr_id: UUID,
        channels: List[HikvisionChannel],
    ) -> int:
        """
        Replace all channels for an NVR atomically.

        Strategy:
          1. Delete all existing channels for this NVR.
          2. Bulk-insert the new channel list.

        This is simpler and safer than a per-channel upsert because:
          - Channel IDs can be renumbered by firmware upgrades.
          - Deleted channels should not linger in the DB.
          - The whole operation is inside the caller's transaction.

        Returns the number of channels saved.
        """

        if not channels:
            logger.debug("No channels to save for nvr_id=%s", nvr_id)
            return 0

        # 1. Delete stale channels
        await self.db.execute(
            delete(NVRChannel).where(NVRChannel.nvr_id == nvr_id)
        )

        # 2. Bulk insert new channels
        rows = [
            {
                "nvr_id": nvr_id,
                "channel_id": ch.channel_id,
                "channel_name": ch.channel_name,
                "ip_address": ch.ip_address,
                "manage_port": ch.manage_port,
                "protocol": ch.protocol,
                "is_enabled": ch.enabled,
            }
            for ch in channels
        ]

        await self.db.execute(pg_insert(NVRChannel), rows)

        logger.debug(
            "Saved %d channels for nvr_id=%s", len(rows), nvr_id
        )
        return len(rows)

    async def list_channels(
        self,
        nvr_id: UUID,
    ) -> List[NVRChannel]:
        """Return all channels for a given NVR, ordered by channel_id."""
        result = await self.db.execute(
            select(NVRChannel)
            .where(NVRChannel.nvr_id == nvr_id)
            .order_by(NVRChannel.channel_id)
        )
        return list(result.scalars().all())
