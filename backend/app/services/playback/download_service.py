"""
services/playback/download_service.py

Recording clip download/export foundation.

Phase 9 provides the foundation for clip export.  Full implementation
(background transcoding, progress tracking, S3 upload) is deferred to
a future phase.

Current capabilities:
  - Validate download request (device, channel, time range)
  - Build Hikvision ISAPI download URL for direct proxy
  - Stream the response back to the client via FastAPI StreamingResponse

Hikvision ISAPI download endpoint:
  GET /ISAPI/ContentMgmt/download
      ?playbackURI=rtsp://<ip>/Streaming/tracks/<track>
          ?starttime=<T>&endtime=<T>

Alternative (some firmware):
  POST /ISAPI/ContentMgmt/download
  Body: <downloadRequest>...</downloadRequest>
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import httpx

from app.models.discovered_nvr import DiscoveredNVR
from app.services.playback.hikvision_playback import (
    build_playback_rtsp_url,
    channel_to_track_id,
    _format_rtsp_dt,
    PlaybackSearchError,
)

logger = logging.getLogger(__name__)

DOWNLOAD_CONNECT_TIMEOUT = 15.0
DOWNLOAD_READ_TIMEOUT = 300.0  # large files can take a while
CHUNK_SIZE = 64 * 1024  # 64 KB chunks


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DownloadError(Exception):
    """Raised when a recording download fails."""


# ---------------------------------------------------------------------------
# Download URL builder
# ---------------------------------------------------------------------------

def build_download_url(
    nvr_ip: str,
    http_port: int,
    channel: int,
    start_time: datetime,
    end_time: datetime,
    use_https: bool = False,
) -> str:
    """
    Build the Hikvision ISAPI download URL.

    The URL embeds the playback RTSP URI as a query parameter.
    This is the standard Hikvision approach for clip export.

    NOTE: This URL contains no credentials — auth is handled via
    Digest Auth on the HTTP request itself.
    """
    track_id = channel_to_track_id(channel)
    start_str = _format_rtsp_dt(start_time)
    end_str = _format_rtsp_dt(end_time)

    scheme = "https" if use_https else "http"
    playback_uri = (
        f"rtsp://{nvr_ip}/Streaming/tracks/{track_id}"
        f"?starttime={start_str}&endtime={end_str}"
    )

    return (
        f"{scheme}://{nvr_ip}:{http_port}/ISAPI/ContentMgmt/download"
        f"?playbackURI={playback_uri}"
    )


# ---------------------------------------------------------------------------
# Streaming download proxy
# ---------------------------------------------------------------------------

async def stream_recording_download(
    nvr: DiscoveredNVR,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> AsyncIterator[bytes]:
    """
    Async generator that proxies a recording download from the NVR.

    Yields raw bytes chunks suitable for use with FastAPI StreamingResponse.

    Usage:
        return StreamingResponse(
            stream_recording_download(nvr, channel, start, end),
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="clip.mp4"'},
        )

    Raises DownloadError on connection or auth failure.
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    download_url = build_download_url(
        nvr_ip=nvr.nvr_ip,
        http_port=nvr.http_port,
        channel=channel,
        start_time=start_time,
        end_time=end_time,
    )

    logger.info(
        "Starting recording download: NVR=%s ch=%d %s → %s",
        nvr.nvr_ip, channel,
        start_time.isoformat(), end_time.isoformat(),
    )

    try:
        async with httpx.AsyncClient(
            auth=httpx.DigestAuth(nvr.username, nvr.password),
            timeout=httpx.Timeout(
                connect=DOWNLOAD_CONNECT_TIMEOUT,
                read=DOWNLOAD_READ_TIMEOUT,
                write=10.0,
                pool=5.0,
            ),
            verify=False,
            follow_redirects=True,
        ) as client:
            async with client.stream("GET", download_url) as response:
                if response.status_code in (401, 403):
                    raise DownloadError(
                        f"Authentication failed for download from {nvr.nvr_ip} "
                        f"(HTTP {response.status_code})"
                    )
                if not response.is_success:
                    raise DownloadError(
                        f"Download request failed: HTTP {response.status_code} "
                        f"from {nvr.nvr_ip}"
                    )

                async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                    yield chunk

    except httpx.TimeoutException as exc:
        raise DownloadError(f"Timeout downloading from {nvr.nvr_ip}: {exc}") from exc
    except httpx.ConnectError as exc:
        raise DownloadError(f"Cannot connect to {nvr.nvr_ip} for download: {exc}") from exc
    except httpx.RequestError as exc:
        raise DownloadError(f"Network error during download from {nvr.nvr_ip}: {exc}") from exc


def build_download_filename(
    nvr_ip: str,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> str:
    """
    Generate a descriptive filename for the downloaded clip.

    Format: recording_<ip>_ch<N>_<start>_<end>.mp4
    """
    ip_safe = nvr_ip.replace(".", "_")
    start_str = start_time.strftime("%Y%m%dT%H%M%S")
    end_str = end_time.strftime("%Y%m%dT%H%M%S")
    return f"recording_{ip_safe}_ch{channel}_{start_str}_{end_str}.mp4"
