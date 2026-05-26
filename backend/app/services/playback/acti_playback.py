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

from datetime import datetime, timezone
from urllib.parse import quote


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
    Build the go2rtc FFmpeg source URL for ACTi SNVR recording playback.

    The `sec` parameter is a Unix timestamp (UTC).  The NVR seeks to that
    position in its recording index and streams from there.

    Parameters
    ----------
    nvr_ip, http_port : NVR address
    username, password : credentials
    channel : 1-based channel number
    start_time : playback start (UTC datetime)
    i_only : 1 = I-frames only (fast seek), 0 = normal playback

    Returns
    -------
    str
        go2rtc stream source string, e.g.:
        "ffmpeg:http://admin:pass@192.168.15.200:80/playback/?cmd=1&channel=1&sec=1748217600&usec=0&mode=0&i_only=0#video=h264"
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    unix_ts = int(start_time.timestamp())
    creds = f"{quote(username, safe='')}:{quote(password, safe='')}"
    path = (
        f"/playback/?cmd=1&channel={channel}"
        f"&sec={unix_ts}&usec=0&mode=0&i_only={i_only}"
    )
    http_url = f"http://{creds}@{nvr_ip}:{http_port}{path}"
    return f"ffmpeg:{http_url}#video=h264"
