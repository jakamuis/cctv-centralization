"""
services/playback/playback_manager.py

Orchestrates the full playback session lifecycle.

Responsibilities:
  1. Validate device exists and is reachable
  2. Generate authenticated RTSP playback URL (credentials never leave backend)
  3. Register temporary stream in go2rtc via REST API
  4. Create PlaybackSession record in DB + Redis
  5. Return tokenized stream URL for frontend consumption
  6. Destroy session: remove go2rtc stream + DB record

go2rtc stream registration:
  POST /api/streams
  Body: {"name": "<stream_name>", "channels": {"0": {"url": "<rtsp_url>"}}}

go2rtc stream deletion:
  DELETE /api/streams?name=<stream_name>
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.discovered_nvr import DiscoveredNVR
from app.models.playback_session import PlaybackSession
from app.services.playback.hikvision_playback import build_playback_rtsp_url
from app.services.playback.playback_session import (
    create_session,
    delete_session,
    DEFAULT_SESSION_TTL_SECONDS,
)

logger = logging.getLogger(__name__)

# go2rtc REST API timeout
GO2RTC_TIMEOUT = 10.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PlaybackManagerError(Exception):
    """General playback manager error."""


class DeviceNotFoundError(PlaybackManagerError):
    """Raised when the requested device does not exist."""


class Go2RTCError(PlaybackManagerError):
    """Raised when go2rtc stream registration/deletion fails."""


# ---------------------------------------------------------------------------
# go2rtc integration
# ---------------------------------------------------------------------------

def _build_stream_name(device_id: uuid.UUID, channel: int, start_time: datetime) -> str:
    """
    Generate a unique, deterministic stream name for a playback session.

    Format: playback_<device_id_short>_ch<channel>_<timestamp>

    Example: playback_a1b2c3d4_ch1_20260523T000000Z
    """
    device_short = str(device_id).replace("-", "")[:8]
    ts = start_time.strftime("%Y%m%dT%H%M%SZ") if start_time.tzinfo else start_time.strftime("%Y%m%dT%H%M%SZ")
    return f"playback_{device_short}_ch{channel}_{ts}"


async def _register_go2rtc_stream(stream_name: str, rtsp_url: str) -> None:
    """
    Register a temporary playback stream in go2rtc.

    go2rtc API:
      POST /api/streams
      Content-Type: application/json
      Body: {"name": "...", "channels": {"0": {"url": "rtsp://..."}}}

    Raises Go2RTCError on failure.
    """
    api_url = f"{settings.streaming.internal_go2rtc_url}/api/streams"
    payload = {
        "name": stream_name,
        "channels": {
            "0": {"url": rtsp_url}
        },
    }

    logger.info("Registering go2rtc playback stream: %r", stream_name)

    try:
        async with httpx.AsyncClient(timeout=GO2RTC_TIMEOUT) as client:
            response = await client.post(api_url, json=payload)
    except httpx.RequestError as exc:
        raise Go2RTCError(f"Cannot reach go2rtc at {api_url}: {exc}") from exc

    if not response.is_success:
        raise Go2RTCError(
            f"go2rtc stream registration failed: HTTP {response.status_code} — {response.text[:200]}"
        )

    logger.info("go2rtc stream registered: %r", stream_name)


async def _delete_go2rtc_stream(stream_name: str) -> None:
    """
    Remove a temporary playback stream from go2rtc.

    go2rtc API:
      DELETE /api/streams?name=<stream_name>

    Errors are logged but not re-raised (best-effort cleanup).
    """
    api_url = f"{settings.streaming.internal_go2rtc_url}/api/streams"

    logger.info("Removing go2rtc playback stream: %r", stream_name)

    try:
        async with httpx.AsyncClient(timeout=GO2RTC_TIMEOUT) as client:
            response = await client.delete(api_url, params={"name": stream_name})
        if not response.is_success:
            logger.warning(
                "go2rtc stream deletion returned HTTP %d for stream %r: %s",
                response.status_code, stream_name, response.text[:200],
            )
        else:
            logger.info("go2rtc stream removed: %r", stream_name)
    except httpx.RequestError as exc:
        logger.warning("Cannot reach go2rtc to delete stream %r: %s", stream_name, exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_playback_session(
    db: AsyncSession,
    nvr: DiscoveredNVR,
    channel: int,
    start_time: datetime,
    end_time: datetime,
    created_by: Optional[int] = None,
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
) -> PlaybackSession:
    """
    Full playback session creation flow:

    1. Build authenticated RTSP URL (credentials stay in backend)
    2. Generate unique stream name
    3. Register stream in go2rtc
    4. Persist PlaybackSession to DB + Redis
    5. Return PlaybackSession (stream_name is the go2rtc key)

    The frontend receives only the stream_name and constructs the
    WebSocket URL itself (same as live view).

    Raises:
      Go2RTCError       — if go2rtc registration fails
      PlaybackManagerError — for other orchestration errors
    """
    # Ensure start/end are UTC-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    stream_name = _build_stream_name(nvr.id, channel, start_time)

    # Build the authenticated RTSP URL — never sent to frontend
    rtsp_url = build_playback_rtsp_url(
        nvr_ip=nvr.nvr_ip,
        rtsp_port=nvr.rtsp_port,
        username=nvr.username,
        password=nvr.password,
        channel=channel,
        start_time=start_time,
        end_time=end_time,
    )

    # Register in go2rtc
    await _register_go2rtc_stream(stream_name, rtsp_url)

    # Persist session
    try:
        session = await create_session(
            db=db,
            device_id=nvr.id,
            channel=channel,
            start_time=start_time,
            end_time=end_time,
            stream_name=stream_name,
            created_by=created_by,
            ttl_seconds=ttl_seconds,
        )
    except Exception as exc:
        # If DB write fails, clean up the go2rtc stream we just registered
        logger.error("DB session creation failed, rolling back go2rtc stream: %s", exc)
        await _delete_go2rtc_stream(stream_name)
        raise PlaybackManagerError(f"Failed to create playback session: {exc}") from exc

    return session


async def destroy_playback_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> bool:
    """
    Destroy a playback session:

    1. Look up the session
    2. Delete go2rtc stream (best-effort)
    3. Delete DB + Redis records

    Returns True if the session existed and was destroyed.
    """
    from app.services.playback.playback_session import get_session

    session = await get_session(db, session_id)
    if not session:
        logger.warning("destroy_playback_session: session %s not found", session_id)
        return False

    stream_name = session.stream_name

    # Remove go2rtc stream first (best-effort)
    await _delete_go2rtc_stream(stream_name)

    # Remove DB + Redis records
    deleted = await delete_session(db, session_id)

    logger.info("Destroyed playback session %s (stream=%r)", session_id, stream_name)
    return deleted


def build_playback_stream_url(stream_name: str) -> str:
    """
    Build the frontend-facing WebSocket/MSE URL for a playback stream.

    Uses the same go2rtc WebSocket path as live view — the only difference
    is the stream_name parameter.

    The frontend connects to:
      ws://<host>/go2rtc/api/ws?src=<stream_name>

    This function returns the relative path that the frontend can use
    to construct the full URL based on window.location.host.
    """
    return f"/go2rtc/api/ws?src={stream_name}"
