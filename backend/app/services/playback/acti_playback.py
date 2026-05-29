"""
services/playback/acti_playback.py

URL builders for ACTi SNVR live streaming and playback.

Why this file exists:
  - ACTi SNVRs stream H.264 over HTTP (multipart/x-mixed-replace) rather than
    RTSP, so go2rtc requires an FFmpeg wrapper source instead of a plain RTSP URL.
  - Keeping URL construction here isolates ACTi-specific knowledge from the
    playback manager.

Stream format (discovered by probing 192.168.15.200):
  Live:    GET /virtualcamera/channel{N}?media&streamid=0
  Playback: GET /playback/?cmd=1&channel={N}&sec={unix_ts}&usec=0&mode=0&i_only=0

Both endpoints return:
  HTTP/1.0 200 OK
  Content-Type: multipart/x-mixed-replace; boundary=myboundary
  [each part: Content-Type: video/h264 + H.264 Annex B chunk]

go2rtc source format:
  "ffmpeg:http://user:pass@ip:port/path#video=h264"
  FFmpeg uses its mpjpeg demuxer to split the multipart stream and passes
  the raw H.264 to go2rtc.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

TEMP_DIR = os.environ.get("PLAYBACK_CACHE_DIR", "/tmp/playback_cache")

# Hard cap: never download more than this many seconds in one session
MAX_PREFETCH_SECONDS = int(os.environ.get("PLAYBACK_MAX_PREFETCH_SECONDS", 3600))
# Wall-clock timeout for the download subprocess (seconds)
PREFETCH_WALL_TIMEOUT = int(os.environ.get("PLAYBACK_PREFETCH_WALL_TIMEOUT", 600))


def build_live_stream_url(
    nvr_ip: str,
    http_port: int,
    username: str,
    password: str,
    channel: int,
    streamid: int = 0,
) -> str:
    """
    Build the go2rtc FFmpeg source URL for an ACTi SNVR live stream.

    Parameters
    ----------
    nvr_ip, http_port : NVR address
    username, password : credentials (embedded in URL for go2rtc/FFmpeg)
    channel : 1-based channel number
    streamid : 0 = main stream, 1 = sub-stream

    Returns
    -------
    str
        go2rtc stream source string, e.g.:
        "ffmpeg:http://admin:pass@192.168.15.200:80/virtualcamera/channel1?media&streamid=0#video=h264"
    """
    creds = f"{quote(username, safe='')}:{quote(password, safe='')}"
    path = f"/virtualcamera/channel{channel}?media&streamid={streamid}"
    http_url = f"http://{creds}@{nvr_ip}:{http_port}{path}"
    return f"ffmpeg:{http_url}#video=h264"


def build_playback_http_url(
    nvr_ip: str,
    http_port: int,
    username: str,
    password: str,
    channel: int,
    start_time: datetime,
    i_only: int = 0,
) -> str:
    """
    Build the go2rtc exec: source for ACTi SNVR recording playback.

    Uses the same acti_pipe.py script as live streams — passing the playback
    path directly so the script fetches from /playback/ instead of /virtualcamera/.

    Returns
    -------
    str
        go2rtc stream source string, e.g.:
        "exec:python3 /scripts/acti_pipe.py 192.168.15.200 /playback/?cmd=1&channel=1&sec=1748217600&usec=0&mode=0&i_only=0 admin 123456#video=h264"
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    unix_ts = int(start_time.timestamp())
    port_arg = f" {http_port}" if http_port != 80 else ""
    return (
        f"exec:python3 /scripts/acti_pipe.py"
        f" --playback {nvr_ip} {channel} {unix_ts}"
        f" {quote(username, safe='')} {quote(password, safe='')}{port_arg}"
        f"#video=h264"
    )


async def download_acti_recording(
    nvr_ip: str,
    http_port: int,
    username: str,
    password: str,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> str:
    """
    Download an ACTi SNVR recording to a server-side MP4 file.

    Pipes: acti_pipe.py --playback  →  ffmpeg  →  /tmp/playback_cache/{uuid}.mp4

    The ffmpeg -t flag caps output at the requested window duration so the
    download stops automatically even if the device keeps streaming.

    Returns the absolute path to the written MP4 file.
    Raises RuntimeError on subprocess failure or timeout.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    unix_ts = int(start_time.timestamp())
    duration = min(
        int((end_time - start_time).total_seconds()),
        MAX_PREFETCH_SECONDS,
    )

    file_id = uuid.uuid4().hex[:16]
    out_path = os.path.join(TEMP_DIR, f"pb_{file_id}.mp4")

    pipe_args = ["--playback", nvr_ip, str(channel), str(unix_ts), username, password]
    if http_port != 80:
        pipe_args.append(str(http_port))

    # Use a real OS pipe so both subprocesses share a kernel pipe buffer.
    # asyncio.StreamReader has no fileno() and cannot be passed as stdin/stdout
    # between two create_subprocess_exec calls directly.
    r_fd, w_fd = os.pipe()

    try:
        pipe_proc = await asyncio.create_subprocess_exec(
            sys.executable, "/scripts/acti_pipe.py", *pipe_args,
            stdout=w_fd,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError:
        os.close(r_fd)
        os.close(w_fd)
        raise RuntimeError("acti_pipe.py not found at /scripts/acti_pipe.py — check backend volume mounts")

    # Parent closes write end — acti_pipe.py owns it; ffmpeg sees EOF when it exits.
    os.close(w_fd)

    try:
        ffmpeg_proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-t", str(duration),
            "-f", "h264", "-i", "pipe:0",
            "-c:v", "copy",
            "-movflags", "faststart",
            out_path,
            stdin=r_fd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        # Python subprocess closes r_fd in the parent after fork — don't close again.
    except FileNotFoundError:
        os.close(r_fd)
        pipe_proc.kill()
        await pipe_proc.wait()
        raise RuntimeError("ffmpeg not found — install ffmpeg in the backend container")

    logger.info(
        "ACTi prefetch started: %s ch%s t=%d duration=%ds → %s",
        nvr_ip, channel, unix_ts, duration, out_path,
    )

    try:
        await asyncio.wait_for(ffmpeg_proc.wait(), timeout=PREFETCH_WALL_TIMEOUT)
    except asyncio.TimeoutError:
        ffmpeg_proc.kill()
        logger.warning("ACTi prefetch timed out: %s ch%s", nvr_ip, channel)
        raise RuntimeError(
            f"Recording download timed out after {PREFETCH_WALL_TIMEOUT}s "
            f"— try a shorter time window"
        )
    finally:
        try:
            pipe_proc.kill()
        except ProcessLookupError:
            pass
        await pipe_proc.wait()

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
        raise RuntimeError("Recording download produced no data — device may have no recording at this time")

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    logger.info("ACTi prefetch complete: %s → %.1f MB", out_path, size_mb)
    return out_path


async def probe_playback_available(
    nvr_ip: str,
    http_port: int,
    username: str,
    password: str,
    channel: int,
    start_time: datetime,
    timeout: float = 4.0,
) -> bool:
    """
    Quick check: does this ACTi SNVR have recordings accessible at start_time?

    Sends a GET to /playback/ and checks for a multipart response header.
    Closes the connection immediately after the headers are received — no
    video data is downloaded.

    Returns True if the device replies HTTP 200 with a multipart content-type
    (indicating recording data is present), False for any other outcome.
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    unix_ts = int(start_time.timestamp())
    path = f"/playback/?cmd=1&channel={channel}&sec={unix_ts}&usec=0&mode=0&i_only=0"
    url = f"http://{nvr_ip}:{http_port}{path}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "GET",
                url,
                auth=(username, password),
                headers={"Connection": "close"},
            ) as response:
                if response.status_code != 200:
                    logger.debug(
                        "ACTi playback probe: HTTP %d from %s ch%s t=%d",
                        response.status_code, nvr_ip, channel, unix_ts,
                    )
                    return False
                content_type = response.headers.get("content-type", "")
                if "multipart" not in content_type.lower():
                    return False

                # Device always returns 200 + multipart header even when there
                # is no recording — wait for at least one Content-Length line
                # inside a part header to confirm real data exists.
                buf = b""
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    buf += chunk
                    if b"Content-Length:" in buf or b"content-length:" in buf:
                        logger.debug(
                            "ACTi playback probe: %s ch%s t=%d → has real data",
                            nvr_ip, channel, unix_ts,
                        )
                        return True
                    if len(buf) > 8192:
                        break

                logger.debug(
                    "ACTi playback probe: %s ch%s t=%d → multipart but no data parts",
                    nvr_ip, channel, unix_ts,
                )
                return False
    except Exception as exc:
        logger.debug("ACTi playback probe failed for %s ch%s: %s", nvr_ip, channel, exc)
        return False
