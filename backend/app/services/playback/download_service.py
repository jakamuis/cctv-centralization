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
import os
import urllib.parse
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.models.discovered_nvr import DiscoveredNVR
from app.services.playback.hikvision_playback import (
    channel_to_track_id,
    _format_rtsp_dt,
)
from app.utils.redis_client import get_redis

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024
FIRST_CHUNK_TIMEOUT = 12  # seconds to wait for first data before trying next URL

# Redis key: nvr_url_hint:{nvr_ip}  → "tracks" | "psia"  (TTL 24 h)
_HINT_KEY_TTL = 86_400

# Per-NVR asyncio locks — prevents two concurrent RTSP playback connections to the
# same device (most NVRs allow only one at a time).
_nvr_locks: dict[str, asyncio.Lock] = {}


def _get_nvr_lock(nvr_ip: str) -> asyncio.Lock:
    if nvr_ip not in _nvr_locks:
        _nvr_locks[nvr_ip] = asyncio.Lock()
    return _nvr_locks[nvr_ip]

TEMP_DIR = os.environ.get("PLAYBACK_CACHE_DIR", "/tmp/playback_cache")
PREFETCH_WALL_TIMEOUT = int(os.environ.get("PLAYBACK_PREFETCH_WALL_TIMEOUT", 600))


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
        "-c:v", "copy", "-c:a", "aac", "-b:a", "64k",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4", "pipe:1",
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
    out_path: str | None = None,
    on_file_complete: "asyncio.coroutines.Coroutine | None" = None,
) -> AsyncGenerator[bytes, None]:
    """
    Async generator — streams fragmented MP4 bytes directly from NVR via ffmpeg.
    Raises DownloadError before the first yield if no URL produces data.

    If out_path is given, a seekable faststart MP4 is written to that path in
    parallel with the HTTP stream (one RTSP connection, two ffmpeg outputs).
    When ffmpeg exits cleanly (end of clip reached), on_file_complete() is awaited
    so the caller can mark the file as ready in Redis.
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

    # Serialise concurrent connections to the same NVR — most devices only support
    # one RTSP playback stream at a time, so a second simultaneous request would
    # immediately fail.  The lock is held only during the probe phase (≤ 2×timeout),
    # not for the full stream duration.
    async with _get_nvr_lock(nvr.nvr_ip):
        # Check Redis for a previously cached URL hint so we can skip the 12 s
        # tracks probe for NVRs that are known to use PSIA only.
        redis = get_redis()
        hint = await redis.get(f"nvr_url_hint:{nvr.nvr_ip}")

        stderr = ""
        if hint != "psia":
            # --- Attempt 1: tracks URL ---
            logger.info(
                "Download attempt 1 (tracks): NVR=%s ch=%d %s→%s",
                nvr.nvr_ip, channel, start_str, end_str,
            )
            proc, first_chunk, stderr = await _try_first_chunk(tracks_url, duration_secs, FIRST_CHUNK_TIMEOUT)
            if first_chunk:
                await redis.set(f"nvr_url_hint:{nvr.nvr_ip}", "tracks", ex=_HINT_KEY_TTL)
            elif stderr:
                logger.warning("tracks failed (stderr: %s)", stderr[:200].strip())
            else:
                logger.warning("tracks: no data in %ds, trying PSIA", FIRST_CHUNK_TIMEOUT)
        else:
            logger.info(
                "Download (PSIA, cached hint): NVR=%s ch=%d %s→%s",
                nvr.nvr_ip, channel, start_str, end_str,
            )

        if first_chunk is None:
            # --- Attempt 2: PSIA URL ---
            logger.info("Download attempt (PSIA): NVR=%s ch=%d", nvr.nvr_ip, channel)
            proc, first_chunk, stderr = await _try_first_chunk(psia_url, duration_secs, FIRST_CHUNK_TIMEOUT)
            if first_chunk:
                await redis.set(f"nvr_url_hint:{nvr.nvr_ip}", "psia", ex=_HINT_KEY_TTL)

            if first_chunk is None:
                if "453" in stderr or not stderr:
                    # --- Attempt 3: free go2rtc slot, retry PSIA ---
                    logger.warning("PSIA blocked (453/no data) — freeing go2rtc slot")
                    freed_stream = await _go2rtc_find_live_stream(nvr.nvr_ip, channel)
                    if freed_stream:
                        await _go2rtc_delete_stream(freed_stream[0])
                        await asyncio.sleep(3)
                    logger.info("Download attempt (PSIA after slot free): NVR=%s ch=%d", nvr.nvr_ip, channel)
                    proc, first_chunk, stderr = await _try_first_chunk(psia_url, duration_secs, FIRST_CHUNK_TIMEOUT)
                    if first_chunk:
                        await redis.set(f"nvr_url_hint:{nvr.nvr_ip}", "psia", ex=_HINT_KEY_TTL)

            if first_chunk is None:
                if freed_stream:
                    await _go2rtc_restore_stream(freed_stream[0], freed_stream[1])
                    freed_stream = None
                raise DownloadError(
                    f"NVR {nvr.nvr_ip} ch={channel}: all URL formats failed. "
                    f"Last error: {stderr[:200].strip() or 'no data received'}"
                )

    # ── File-first streaming (when a cache file is requested) ──────────────────
    # Kill the probe process and restart ffmpeg writing to the file ONLY (no pipe).
    # Then stream to the HTTP client by reading from the file as ffmpeg writes it.
    # This fully decouples the file-write speed (NVR bitrate) from the HTTP client
    # consumption rate — a slow browser doesn't stall ffmpeg or leave a partial file.
    if out_path:
        working_url = tracks_url if (first_chunk and hint != "psia") else psia_url
        await _kill_ffmpeg(proc)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        file_cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-i", working_url,
            "-t", str(duration_secs),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "64k",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-f", "mp4", out_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *file_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for the file to appear with at least the ftyp box (8 bytes)
        deadline = asyncio.get_event_loop().time() + 15.0
        while True:
            if os.path.exists(out_path) and os.path.getsize(out_path) >= 8:
                break
            if proc.returncode is not None:
                err = (await proc.stderr.read()).decode(errors="replace")
                raise DownloadError(
                    f"NVR {nvr.nvr_ip} ch={channel}: file-write ffmpeg exited early: {err[:200]}"
                )
            if asyncio.get_event_loop().time() > deadline:
                await _kill_ffmpeg(proc)
                raise DownloadError(
                    f"NVR {nvr.nvr_ip} ch={channel}: timeout waiting for file data"
                )
            await asyncio.sleep(0.1)

        logger.info("File-based stream started → %s", out_path)
        total_bytes = 0
        clean_exit = False
        try:
            with open(out_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if chunk:
                        total_bytes += len(chunk)
                        yield chunk
                    elif proc.returncode is not None:
                        # ffmpeg finished — drain any bytes written since last read
                        tail = f.read()
                        if tail:
                            total_bytes += len(tail)
                            yield tail
                        clean_exit = (proc.returncode == 0)
                        break
                    else:
                        await asyncio.sleep(0.05)
        finally:
            if proc and proc.returncode is None:
                proc.kill()
            if proc:
                await proc.wait()
            if freed_stream:
                await _go2rtc_restore_stream(freed_stream[0], freed_stream[1])
            logger.info(
                "Stream complete (file): NVR=%s ch=%d %.1f MB rc=%s",
                nvr.nvr_ip, channel, total_bytes / 1_048_576,
                proc.returncode if proc else "?",
            )
            if clean_exit and os.path.exists(out_path) and on_file_complete:
                try:
                    await on_file_complete()
                    logger.info("Cache file ready: %s", out_path)
                except Exception as exc:
                    logger.warning("on_file_complete callback failed: %s", exc)
        return  # generator done — skip the pipe:1 path below

    # ── Pipe streaming (no cache file) ─────────────────────────────────────────
    logger.info("First chunk received (%.1f KB) — streaming started", len(first_chunk) / 1024)

    total_bytes = len(first_chunk)
    yield first_chunk

    clean_exit = False
    try:
        while True:
            try:
                chunk = await asyncio.wait_for(proc.stdout.read(CHUNK_SIZE), timeout=60.0)
            except asyncio.TimeoutError:
                logger.warning("No data from ffmpeg for 60s — ending stream")
                break
            if not chunk:
                clean_exit = True   # stdout EOF = ffmpeg finished the full clip
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


# ---------------------------------------------------------------------------
# Server-side prefetch (download to file)
# ---------------------------------------------------------------------------

async def prefetch_recording_to_file(
    nvr: DiscoveredNVR,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> str:
    """
    Download an NVR recording to a server-side MP4 temp file for browser playback.

    Strategy: write directly to file (no stdout pipe), detect success by polling
    file size — avoids the stdout-buffering race and gives slower NVRs more time
    to start streaming.

    URL fallback: tracks → PSIA → free go2rtc slot + PSIA.
    Returns the absolute path to the file.  Raises DownloadError on failure.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    rtsp_port     = getattr(nvr, "rtsp_port", None) or 554
    start_str     = _format_rtsp_dt(start_time)
    end_str       = _format_rtsp_dt(end_time)
    duration_secs = min(max(1, int((end_time - start_time).total_seconds())), PREFETCH_WALL_TIMEOUT)
    track_id      = channel_to_track_id(channel)

    user_enc = urllib.parse.quote(nvr.username, safe="")
    pass_enc = urllib.parse.quote(nvr.password, safe="")
    base       = f"rtsp://{user_enc}:{pass_enc}@{nvr.nvr_ip}:{rtsp_port}"
    tracks_url = f"{base}/Streaming/tracks/{track_id}?starttime={start_str}&endtime={end_str}"
    psia_url   = f"{base}/PSIA/Streaming/channels/{channel}01?starttime={start_str}&endtime={end_str}"

    # How long to wait for the output file to start growing before trying the next URL.
    # Longer than _try_first_chunk because some NVRs need extra time for playback setup.
    PROBE_TIMEOUT = 25.0

    async def _try_url(rtsp_url: str, out_path: str) -> tuple[asyncio.subprocess.Process | None, bool, str]:
        """
        Start ffmpeg writing to out_path.  Poll file size for up to PROBE_TIMEOUT seconds.
        Returns (proc_or_None, started_writing, stderr).
        - If started_writing=True: proc is still running; caller must await it.
        - If started_writing=False: proc is dead; out_path should be removed.
        """
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-t", str(duration_secs),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "64k",
            "-movflags", "faststart",
            out_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        deadline = asyncio.get_event_loop().time() + PROBE_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(2)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
                return proc, True, ""
            if proc.returncode is not None:
                stderr = (await proc.stderr.read()).decode(errors="replace").strip()
                return None, False, stderr
        # Timeout — kill
        proc.kill()
        try:
            _, sb = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            stderr = sb.decode(errors="replace").strip()
        except asyncio.TimeoutError:
            stderr = ""
        return None, False, stderr

    freed_stream: tuple[str, str] | None = None
    last_stderr = ""

    async def _attempt(rtsp_url: str, label: str) -> tuple[asyncio.subprocess.Process | None, str | None]:
        """Run one URL attempt.  Returns (running_proc, out_path) on success, (None, None) on failure."""
        nonlocal last_stderr
        out = os.path.join(TEMP_DIR, f"pb_{uuid.uuid4().hex[:16]}.mp4")
        logger.info("Prefetch %s: NVR=%s ch=%d", label, nvr.nvr_ip, channel)
        proc, ok, stderr = await _try_url(rtsp_url, out)
        last_stderr = stderr
        if ok:
            return proc, out
        if stderr:
            logger.warning("Prefetch %s failed: %s", label, stderr[-300:])
        # Clean up partial file
        try:
            os.remove(out)
        except OSError:
            pass
        return None, None

    # --- Attempt 1: tracks URL ---
    proc, out_path = await _attempt(tracks_url, "tracks")

    if proc is None:
        # --- Attempt 2: PSIA URL ---
        proc, out_path = await _attempt(psia_url, "PSIA")

        if proc is None and ("453" in last_stderr or not last_stderr):
            # --- Attempt 3: free go2rtc live slot, retry PSIA ---
            freed_stream = await _go2rtc_find_live_stream(nvr.nvr_ip, channel)
            if freed_stream:
                await _go2rtc_delete_stream(freed_stream[0])
                await asyncio.sleep(3)
            proc, out_path = await _attempt(psia_url, "PSIA-after-slot-free")

    if proc is None or out_path is None:
        if freed_stream:
            await _go2rtc_restore_stream(freed_stream[0], freed_stream[1])
        raise DownloadError(
            f"NVR {nvr.nvr_ip} ch={channel}: all URL formats failed — "
            f"{last_stderr[-300:].strip() or 'no data received from device'}"
        )

    # File started growing — wait for ffmpeg to finish the full clip
    logger.info("Prefetch writing: NVR=%s ch=%d → %s  (duration=%ds)", nvr.nvr_ip, channel, out_path, duration_secs)
    try:
        _, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=float(PREFETCH_WALL_TIMEOUT)
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        if freed_stream:
            await _go2rtc_restore_stream(freed_stream[0], freed_stream[1])
        raise DownloadError(
            f"Recording download timed out after {PREFETCH_WALL_TIMEOUT}s — try a shorter time window"
        )

    if freed_stream:
        await _go2rtc_restore_stream(freed_stream[0], freed_stream[1])

    stderr_str = stderr_bytes.decode(errors="replace").strip() if stderr_bytes else ""
    if stderr_str:
        logger.warning("[ffmpeg prefetch] %s", stderr_str)

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
        raise DownloadError(
            f"Recording produced no data — "
            f"{stderr_str[-300:] or 'device may have no recordings at this time'}"
        )

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    logger.info("Prefetch complete: %s → %.1f MB", out_path, size_mb)
    return out_path
