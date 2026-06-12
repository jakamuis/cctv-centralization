"""
services/playback/download_service.py

Recording download — ffmpeg streams directly to the HTTP response.

URL resolution strategy (no pre-probe — uses first-chunk detection):
  1. Try /Streaming/tracks/{track}?starttime=... with a 10s first-chunk timeout.
  2. If no data or 453 in stderr → try PSIA /PSIA/Streaming/channels/{channel}01?starttime=...
  3. If PSIA also fails → free go2rtc live-stream slot and retry PSIA.
  4. Raise DownloadError if all attempts produce no first chunk.

Once the first chunk arrives the StreamingResponse starts immediately —
the browser shows real download progress.
"""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.models.discovered_nvr import DiscoveredNVR
from app.services.playback.hikvision_playback import (
    channel_to_track_id,
    _format_rtsp_dt,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024
FIRST_CHUNK_TIMEOUT = 12  # seconds to wait for first data before trying next URL


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DownloadError(Exception):
    """Raised when a recording download fails (before any bytes are streamed)."""


# ---------------------------------------------------------------------------
# go2rtc slot management
# ---------------------------------------------------------------------------

async def _go2rtc_find_live_stream(nvr_ip: str, channel: int) -> tuple[str, str] | None:
    go2rtc_url = settings.streaming.internal_go2rtc_url
    channel_patterns = [
        f"/Streaming/Channels/{channel}01",
        f"/Streaming/Channels/{channel:02d}1",
        f"/Streaming/Channels/{channel}",
        f"Channels/{channel}",
    ]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{go2rtc_url}/api/streams")
            if not resp.is_success:
                return None
            for name, info in resp.json().items():
                if name.startswith("playback_"):
                    continue
                for producer in (info.get("producers") or []):
                    url = producer.get("url", "")
                    if nvr_ip in url and any(p in url for p in channel_patterns):
                        return name, url
    except Exception as exc:
        logger.debug("go2rtc stream lookup failed: %s", exc)
    return None


async def _go2rtc_delete_stream(stream_name: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(
                f"{settings.streaming.internal_go2rtc_url}/api/streams",
                params={"name": stream_name},
            )
        logger.info("go2rtc: freed live stream %r for download", stream_name)
    except Exception as exc:
        logger.warning("go2rtc delete stream failed: %s", exc)


async def _go2rtc_restore_stream(stream_name: str, source_url: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.put(
                f"{settings.streaming.internal_go2rtc_url}/api/streams",
                params={"name": stream_name, "src": source_url},
            )
        logger.info("go2rtc: restored live stream %r", stream_name)
    except Exception as exc:
        logger.warning("go2rtc restore stream failed: %s", exc)


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

def _make_ffmpeg_cmd(rtsp_url: str, duration_secs: int) -> list[str]:
    return [
        "ffmpeg", "-y", "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-t", str(duration_secs),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "64k",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4",
        "pipe:1",
    ]


async def _start_ffmpeg(rtsp_url: str, duration_secs: int) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *_make_ffmpeg_cmd(rtsp_url, duration_secs),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def _kill_ffmpeg(proc: asyncio.subprocess.Process) -> str:
    """Kill an ffmpeg process and return its stderr."""
    if proc.returncode is None:
        proc.kill()
    try:
        _, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=5.0)
    except asyncio.TimeoutError:
        stderr_bytes = b""
    return stderr_bytes.decode(errors="replace")


async def _try_first_chunk(
    rtsp_url: str, duration_secs: int, timeout: float
) -> tuple[asyncio.subprocess.Process, bytes | None, str]:
    """
    Start ffmpeg and try to get the first chunk within `timeout` seconds.
    Returns (proc, first_chunk_or_None, stderr_so_far).
    If first_chunk is None, proc has been killed and stderr is populated.
    """
    proc = await _start_ffmpeg(rtsp_url, duration_secs)
    try:
        chunk = await asyncio.wait_for(proc.stdout.read(CHUNK_SIZE), timeout=timeout)
        if chunk:
            return proc, chunk, ""
        # EOF with no data
        stderr = await _kill_ffmpeg(proc)
        return proc, None, stderr
    except asyncio.TimeoutError:
        stderr = await _kill_ffmpeg(proc)
        return proc, None, stderr


# ---------------------------------------------------------------------------
# Public: streaming generator
# ---------------------------------------------------------------------------

async def stream_recording(
    nvr: DiscoveredNVR,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> AsyncGenerator[bytes, None]:
    """
    Async generator — streams fragmented MP4 bytes directly from NVR via ffmpeg.
    Raises DownloadError before the first yield if no URL produces data.
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    rtsp_port     = getattr(nvr, "rtsp_port", None) or 554
    start_str     = _format_rtsp_dt(start_time)
    end_str       = _format_rtsp_dt(end_time)
    duration_secs = max(1, int((end_time - start_time).total_seconds()))
    track_id      = channel_to_track_id(channel)

    user_enc = urllib.parse.quote(nvr.username, safe="")
    pass_enc = urllib.parse.quote(nvr.password, safe="")

    base = f"rtsp://{user_enc}:{pass_enc}@{nvr.nvr_ip}:{rtsp_port}"
    tracks_url = f"{base}/Streaming/tracks/{track_id}?starttime={start_str}&endtime={end_str}"
    psia_url   = f"{base}/PSIA/Streaming/channels/{channel}01?starttime={start_str}&endtime={end_str}"

    freed_stream: tuple[str, str] | None = None
    proc: asyncio.subprocess.Process | None = None
    first_chunk: bytes | None = None

    # --- Attempt 1: tracks URL ---
    logger.info("Download attempt 1 (tracks): NVR=%s ch=%d %s→%s", nvr.nvr_ip, channel, start_str, end_str)
    proc, first_chunk, stderr = await _try_first_chunk(tracks_url, duration_secs, FIRST_CHUNK_TIMEOUT)

    if first_chunk is None:
        if stderr:
            logger.warning("tracks failed (stderr: %s)", stderr[:200].strip())
        else:
            logger.warning("tracks: no data in %ds, trying PSIA", FIRST_CHUNK_TIMEOUT)

        # --- Attempt 2: PSIA URL ---
        logger.info("Download attempt 2 (PSIA): NVR=%s ch=%d", nvr.nvr_ip, channel)
        proc, first_chunk, stderr = await _try_first_chunk(psia_url, duration_secs, FIRST_CHUNK_TIMEOUT)

        if first_chunk is None:
            if "453" in stderr or not stderr:
                # --- Attempt 3: free go2rtc slot, retry PSIA ---
                logger.warning("PSIA also blocked (453/no data) — freeing go2rtc slot")
                freed_stream = await _go2rtc_find_live_stream(nvr.nvr_ip, channel)
                if freed_stream:
                    await _go2rtc_delete_stream(freed_stream[0])
                    await asyncio.sleep(3)
                logger.info("Download attempt 3 (PSIA after slot free): NVR=%s ch=%d", nvr.nvr_ip, channel)
                proc, first_chunk, stderr = await _try_first_chunk(psia_url, duration_secs, FIRST_CHUNK_TIMEOUT)

        if first_chunk is None:
            if freed_stream:
                await _go2rtc_restore_stream(freed_stream[0], freed_stream[1])
                freed_stream = None
            raise DownloadError(
                f"NVR {nvr.nvr_ip} ch={channel}: all URL formats failed. "
                f"Last error: {stderr[:200].strip() or 'no data received'}"
            )

    logger.info("First chunk received (%.1f KB) — streaming started", len(first_chunk) / 1024)

    total_bytes = len(first_chunk)
    yield first_chunk

    try:
        while True:
            try:
                chunk = await asyncio.wait_for(proc.stdout.read(CHUNK_SIZE), timeout=60.0)
            except asyncio.TimeoutError:
                logger.warning("No data from ffmpeg for 60s — ending stream")
                break
            if not chunk:
                break
            total_bytes += len(chunk)
            yield chunk
    finally:
        if proc and proc.returncode is None:
            proc.kill()
        if proc:
            await proc.wait()
        if freed_stream:
            await _go2rtc_restore_stream(freed_stream[0], freed_stream[1])
        logger.info("Stream complete: NVR=%s ch=%d %.1f MB", nvr.nvr_ip, channel, total_bytes / 1_048_576)


# ---------------------------------------------------------------------------
# Filename helper
# ---------------------------------------------------------------------------

def build_download_filename(
    nvr_ip: str,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> str:
    ip_safe   = nvr_ip.replace(".", "_")
    start_str = start_time.strftime("%Y%m%dT%H%M%S")
    end_str   = end_time.strftime("%Y%m%dT%H%M%S")
    return f"recording_{ip_safe}_ch{channel}_{start_str}_{end_str}.mp4"
