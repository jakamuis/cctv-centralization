"""
services/playback/playback_manager.py

Orchestrates the full playback session lifecycle.

Responsibilities:
  1. Validate device exists and is reachable
  2. Generate authenticated RTSP playback URL (credentials never leave backend)
  3. Register temporary stream in go2rtc by writing to go2rtc.yaml
     (go2rtc watches the file and auto-reloads within ~1 second)
  4. Create PlaybackSession record in DB + Redis
  5. Return stream_name for frontend WebSocket connection
  6. Destroy session: remove go2rtc stream entry + DB record

go2rtc config file management:
  The go2rtc HTTP API (PUT /api/streams) does not work in v1.9.14.
  Instead, the backend writes directly to go2rtc.yaml (shared Docker volume).
  go2rtc detects the inotify change and reloads streams automatically.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
import yaml
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

# Path to go2rtc config (shared volume — set via GO2RTC_CONFIG_PATH env var)
_GO2RTC_CONFIG_PATH = os.environ.get("GO2RTC_CONFIG_PATH", "/go2rtc.yaml")

# go2rtc Docker container name (for SIGHUP reload via Docker API)
_GO2RTC_CONTAINER = os.environ.get("GO2RTC_CONTAINER_NAME", "cctv_go2rtc")

# Docker daemon Unix socket path
_DOCKER_SOCK = "/var/run/docker.sock"

# Asyncio lock — prevents concurrent config file writes within this process
_config_lock = asyncio.Lock()

# Seconds to wait after go2rtc restart for it to come back online
_GO2RTC_RELOAD_WAIT = 3.0


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
# go2rtc config file helpers
# ---------------------------------------------------------------------------

def _read_go2rtc_config() -> dict:
    """Read and parse go2rtc.yaml. Returns empty dict on missing/invalid file."""
    try:
        with open(_GO2RTC_CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        logger.warning("go2rtc config not found at %s", _GO2RTC_CONFIG_PATH)
        return {}
    except Exception as exc:
        logger.error("Failed to read go2rtc config: %s", exc)
        return {}


def _write_go2rtc_config(config: dict) -> None:
    """Write config dict back to go2rtc.yaml."""
    with open(_GO2RTC_CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


async def _restart_go2rtc() -> None:
    """
    Restart the go2rtc container via the Docker API over the Unix socket.

    go2rtc reads go2rtc.yaml fresh on every startup, so restarting it is
    the only reliable way to add/remove streams dynamically in v1.9.14
    (the PUT /api/streams HTTP API silently ignores requests).

    The restart causes ~3s of downtime for all WebSocket streams, but
    Docker's restart policy brings it back immediately.

    Errors are logged but not re-raised.
    """
    try:
        transport = httpx.AsyncHTTPTransport(uds=_DOCKER_SOCK)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            r = await client.post(f"/containers/{_GO2RTC_CONTAINER}/restart?t=2")
            if r.status_code == 204:
                logger.info("Restarted go2rtc container (%s)", _GO2RTC_CONTAINER)
            else:
                logger.warning(
                    "go2rtc restart returned HTTP %d (container=%s): %s",
                    r.status_code, _GO2RTC_CONTAINER, r.text[:200],
                )
    except Exception as exc:
        logger.warning("Failed to restart go2rtc: %s", exc)


async def _register_go2rtc_stream(stream_name: str, rtsp_url: str) -> None:
    """
    Register a temporary playback stream in go2rtc.

    Writes to go2rtc.yaml, sends SIGHUP to go2rtc via Docker API,
    then waits for the reload to complete.

    Raises Go2RTCError on failure.
    """
    logger.info("Registering go2rtc playback stream: %r", stream_name)

    async with _config_lock:
        try:
            config = _read_go2rtc_config()
            if "streams" not in config or not isinstance(config.get("streams"), dict):
                config["streams"] = {}
            config["streams"][stream_name] = [rtsp_url]
            _write_go2rtc_config(config)
        except Exception as exc:
            raise Go2RTCError(
                f"Failed to write go2rtc config for stream {stream_name!r}: {exc}"
            ) from exc

    await _restart_go2rtc()
    await asyncio.sleep(_GO2RTC_RELOAD_WAIT)
    logger.info("go2rtc stream registered: %r", stream_name)


async def _delete_go2rtc_stream(stream_name: str) -> None:
    """
    Remove a temporary playback stream from go2rtc.yaml and reload go2rtc.

    Errors are logged but not re-raised (best-effort cleanup).
    """
    logger.info("Removing go2rtc playback stream: %r", stream_name)

    async with _config_lock:
        try:
            config = _read_go2rtc_config()
            streams = config.get("streams", {})
            if stream_name in streams:
                del streams[stream_name]
                config["streams"] = streams
                _write_go2rtc_config(config)
                logger.info("go2rtc stream removed from config: %r", stream_name)
            else:
                logger.warning("go2rtc stream %r not found in config (already deleted?)", stream_name)
        except Exception as exc:
            logger.warning("Failed to remove go2rtc stream %r from config: %s", stream_name, exc)
            return

    await _restart_go2rtc()


# ---------------------------------------------------------------------------
# Stream name builder
# ---------------------------------------------------------------------------

def _build_stream_name(device_id: uuid.UUID, channel: int, start_time: datetime) -> str:
    """
    Generate a unique, deterministic stream name for a playback session.

    Format: pb_<device_id_short>_ch<channel>_<timestamp>
    """
    device_short = str(device_id).replace("-", "")[:8]
    ts = start_time.strftime("%Y%m%dT%H%M%SZ") if start_time.tzinfo else start_time.strftime("%Y%m%dT%H%M%SZ")
    return f"pb_{device_short}_ch{channel}_{ts}"


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
    3. Write stream to go2rtc.yaml and wait for go2rtc to reload
    4. Persist PlaybackSession to DB + Redis
    5. Return PlaybackSession (stream_name is the go2rtc key)

    Raises:
      Go2RTCError       — if go2rtc config write fails
      PlaybackManagerError — for other orchestration errors
    """
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

    # Register in go2rtc config file
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
    2. Remove stream from go2rtc.yaml (best-effort)
    3. Delete DB + Redis records

    Returns True if the session existed and was destroyed.
    """
    from app.services.playback.playback_session import get_session

    session = await get_session(db, session_id)
    if not session:
        logger.warning("destroy_playback_session: session %s not found", session_id)
        return False

    stream_name = session.stream_name

    # Remove from go2rtc config (best-effort)
    await _delete_go2rtc_stream(stream_name)

    # Remove DB + Redis records
    deleted = await delete_session(db, session_id)

    logger.info("Destroyed playback session %s (stream=%r)", session_id, stream_name)
    return deleted


def build_playback_stream_url(stream_name: str) -> str:
    """
    Build the frontend-facing WebSocket/MSE URL for a playback stream.

    The frontend connects to:
      ws://<host>/go2rtc/api/ws?src=<stream_name>

    Returns the relative path the frontend uses to construct the full URL.
    """
    return f"/go2rtc/api/ws?src={stream_name}"
