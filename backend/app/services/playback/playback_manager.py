"""
services/playback/playback_manager.py

Orchestrates the full playback session lifecycle.

All vendors use server-side prefetch: the recording is downloaded to a temp
MP4 file first, then served via /session/{id}/stream so the browser gets a
seekable file.  go2rtc is no longer used for playback sessions.

Responsibilities:
  1. Download recording to server-side temp file (all vendors)
  2. Create PlaybackSession record in DB + Redis (temp_file_path stored)
  3. Return session ID — frontend fetches /session/{id}/stream to play
  4. Destroy session: delete temp file + DB + Redis records
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.discovered_nvr import DiscoveredNVR
from app.models.playback_session import PlaybackSession
from app.services.playback.acti_playback import download_acti_recording
from app.services.playback.playback_session import (
    create_session,
    delete_session,
    get_session_temp_file_path,
    mark_session_file_complete,
    set_session_temp_file,
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


class PrefetchError(PlaybackManagerError):
    """Raised when the ACTi recording download to server fails."""


# ---------------------------------------------------------------------------
# go2rtc integration
# ---------------------------------------------------------------------------

def _build_stream_name(device_id: uuid.UUID, channel: int, start_time: datetime) -> str:
    """
    Generate a unique stream name for a playback session.

    Format: playback_<device_id_short>_ch<channel>_<timestamp>_<nonce>

    Example: playback_a1b2c3d4_ch1_20260523T000000Z_f00d1234
    """
    device_short = str(device_id).replace("-", "")[:8]
    ts = start_time.strftime("%Y%m%dT%H%M%SZ") if start_time.tzinfo else start_time.strftime("%Y%m%dT%H%M%SZ")
    nonce = uuid.uuid4().hex[:8]
    return f"playback_{device_short}_ch{channel}_{ts}_{nonce}"


def _delete_temp_file(path: str) -> None:
    """Remove a prefetch temp file, ignoring missing-file errors."""
    import os
    try:
        os.remove(path)
        logger.debug("Deleted temp file: %s", path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning("Could not delete temp file %s: %s", path, exc)


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

    1. Download recording to server-side temp MP4 file
    2. Generate unique stream name (used as session identifier)
    3. Persist PlaybackSession to DB + Redis (temp_file_path stored)
    4. Return PlaybackSession — frontend fetches /session/{id}/stream

    Raises:
      PrefetchError        — if the recording download fails
      PlaybackManagerError — for other orchestration errors
    """
    # Ensure start/end are UTC-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    stream_name = _build_stream_name(nvr.id, channel, start_time)
    vendor = getattr(nvr, "vendor", "hikvision") or "hikvision"

    clip_secs = max(0, int((end_time - start_time).total_seconds()))
    # Give the session enough TTL to cover the full background pre-fetch + buffer.
    effective_ttl = max(ttl_seconds, clip_secs + 300)

    temp_file_path: str | None = None

    if vendor == "acti_snvr":
        # ACTi has no RTSP playback — must download to server first.
        try:
            temp_file_path = await download_acti_recording(
                nvr_ip=nvr.nvr_ip,
                http_port=nvr.http_port,
                username=nvr.username,
                password=nvr.password,
                channel=channel,
                start_time=start_time,
                end_time=end_time,
            )
        except RuntimeError as exc:
            raise PrefetchError(str(exc)) from exc

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
            ttl_seconds=effective_ttl,
            temp_file_path=temp_file_path,
        )
    except Exception as exc:
        logger.error("DB session creation failed: %s", exc)
        if temp_file_path:
            _delete_temp_file(temp_file_path)
        raise PlaybackManagerError(f"Failed to create playback session: {exc}") from exc

    # For non-ACTi vendors: kick off a background download so the full file is on
    # disk before the frontend shows the video player. This gives the browser a
    # seekable FileResponse instead of an un-seekable chunked StreamingResponse.
    if vendor != "acti_snvr":
        from app.services.playback.download_service import TEMP_DIR, stream_recording

        out_path = os.path.join(TEMP_DIR, f"pb_{session.id.hex}.mp4")
        await set_session_temp_file(str(session.id), out_path)

        _sid = str(session.id)

        async def _on_done():
            await mark_session_file_complete(_sid)

        async def _bg_prefetch():
            try:
                async for _ in stream_recording(
                    nvr, channel, start_time, end_time,
                    out_path=out_path, on_file_complete=_on_done,
                ):
                    pass
            except Exception as exc:
                logger.warning("Background prefetch failed session=%s: %s", _sid, exc)

        asyncio.create_task(_bg_prefetch())
        logger.info("Background prefetch started: session=%s out=%s", _sid, out_path)

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

    # Clean up prefetch temp file if present
    temp_path = await get_session_temp_file_path(str(session_id))
    if temp_path:
        _delete_temp_file(temp_path)
    else:
        # Non-prefetched session: remove go2rtc stream (best-effort)
        await _delete_go2rtc_stream(stream_name)

    # Remove DB + Redis records
    deleted = await delete_session(db, session_id)

    logger.info("Destroyed playback session %s (stream=%r)", session_id, stream_name)
    return deleted


