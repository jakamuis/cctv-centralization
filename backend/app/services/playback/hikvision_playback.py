"""
services/playback/hikvision_playback.py

Hikvision ISAPI recording search and playback RTSP URL generation.

DEVICE PROFILE (confirmed from probe on 2026-05-23):
  Model:    DS-7616NI-Q1
  Firmware: V3.4.104 (build 190424)
  Track ID: 101 (channel 1 → track 101, channel N → track N*100+1)
  Recording mode: CMR (Continuous Motion Recording)
  Data namespace: http://www.hikvision.com/ver20/XMLSchema
  Error namespace: urn:psialliance-org  ← only used in ERROR responses
  Working endpoint: /ISAPI/ContentMgmt/search  (POST only)
  Dead endpoints:   /PSIA/* (all 404)

CRITICAL INSIGHT:
  The NVR uses PSIA namespace ONLY for error responses.
  Request XML must use Hikvision namespace or no namespace.
  PSIA-namespace request bodies are always rejected with badXmlContent.

SEARCH MATRIX (ordered by likelihood of success):
  Endpoint:    /ISAPI/ContentMgmt/search only
  Track IDs:   101 (primary), then 1, 1-1 as fallbacks
  Timestamps:  UTC_Z (2026-05-23T00:00:00Z), LOCAL_NO_TZ, HIK_COMPACT
  searchType:  CMR (configured mode), empty (omitted), AllEvent
  XML schemas: no-namespace first, Hikvision-namespace second, PSIA last

The searchType element is critical — V3.x firmware often requires it.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 30.0
MAX_RESULTS = 200

# XML namespaces
HIK_NS = "http://www.hikvision.com/ver20/XMLSchema"
PSIA_NS = "urn:psialliance-org"

# Only ISAPI endpoint works — PSIA returns 404 on this device
_SEARCH_ENDPOINTS = [
    "/ISAPI/ContentMgmt/search",
]

# Probe endpoints (GET only — safe, no auth hammering)
_PROBE_ENDPOINTS = [
    "/ISAPI/ContentMgmt/InputProxy/channels",
    "/ISAPI/ContentMgmt/record/tracks",
    "/ISAPI/System/deviceInfo",
]

_TS_UTC_Z = "UTC_Z"
_TS_LOCAL_NO_TZ = "LOCAL_NO_TZ"
_TS_HIK_COMPACT = "HIK_COMPACT"  # YYYYMMDDTHHMMSSz — used by some V3.x firmware


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RecordingSegment:
    start: datetime
    end: datetime
    track_id: str
    recording_type: str = "normal"


@dataclass
class PlaybackRTSPInfo:
    rtsp_url: str
    stream_name: str
    start_time: datetime
    end_time: datetime


@dataclass
class NVRCapabilities:
    streaming_channels: List[Dict] = field(default_factory=list)
    track_ids: List[str] = field(default_factory=list)
    raw_probe_responses: Dict[str, str] = field(default_factory=dict)
    is_psia: bool = False
    record_search_types: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PlaybackSearchError(Exception):
    pass


class PlaybackRTSPError(Exception):
    pass


# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------

def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def _find_text(element: ET.Element, tag: str) -> Optional[str]:
    for child in element.iter():
        if _strip_ns(child.tag) == tag:
            text = (child.text or "").strip()
            return text if text else None
    return None


def _parse_hikvision_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y%m%dT%H%M%SZ",
        "%Y%m%dT%H%M%S",
    ):
        try:
            return datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Cannot parse datetime: %r", dt_str)
        return None


def _format_isapi_dt_utc_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_NVR_TZ_OFFSETS = {
    "WIB":  timedelta(hours=7),
    "WITA": timedelta(hours=8),
    "WIT":  timedelta(hours=9),
}


def _nvr_tz(nvr_timezone: str) -> timezone:
    offset = _NVR_TZ_OFFSETS.get(nvr_timezone.upper(), timedelta(hours=7))
    return timezone(offset)


def _format_isapi_dt_local_no_tz(dt: datetime, nvr_timezone: str = "WIB") -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(_nvr_tz(nvr_timezone))
    return local_dt.strftime("%Y-%m-%dT%H:%M:%S")


def _format_isapi_dt_hik_compact(dt: datetime) -> str:
    """Hikvision compact format: 20260523T000000Z"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _format_rtsp_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def channel_to_track_id(channel: int) -> int:
    return channel * 100 + 1


# ---------------------------------------------------------------------------
# Track ID candidates
# ---------------------------------------------------------------------------

def _track_id_candidates(channel: int, discovered: Optional[List[str]] = None) -> List[str]:
    """Build ordered list of track ID candidates for a given channel.

    Order:
      1. channel * 100 + 1  (e.g. ch1 → 101, ch2 → 201) — most common Hikvision NVR format
      2. Any discovered track IDs from probe that match this channel
      3. Raw channel number (e.g. 1, 2) — fallback
      4. channel-1 format (e.g. 1-1) — rare fallback

    The probe already filters discovered IDs to connected channels only,
    so we don't need to re-filter here.
    """
    seen: set = set()
    candidates: List[str] = []

    def _add(tid: str) -> None:
        if tid not in seen:
            seen.add(tid)
            candidates.append(tid)

    # Primary: channel * 100 + 1 (standard Hikvision NVR track ID)
    primary = str(channel * 100 + 1)
    _add(primary)

    # Add discovered IDs that match this channel (probe already filtered these)
    if discovered:
        for tid in discovered:
            _add(str(tid))

    # Fallbacks
    _add(str(channel))      # raw channel number
    _add(f"{channel}-1")    # channel-1 format

    logger.debug("Track ID candidates for ch=%d: %s", channel, candidates)
    return candidates


# ---------------------------------------------------------------------------
# Timestamp format candidates
# ---------------------------------------------------------------------------

def _timestamp_candidates(
    start_time: datetime,
    end_time: datetime,
    nvr_timezone: str = "WIB",
) -> List[Tuple[str, str, str]]:
    return [
        (
            _TS_LOCAL_NO_TZ,
            _format_isapi_dt_local_no_tz(start_time, nvr_timezone),
            _format_isapi_dt_local_no_tz(end_time, nvr_timezone),
        ),
        (
            _TS_UTC_Z,
            _format_isapi_dt_utc_z(start_time),
            _format_isapi_dt_utc_z(end_time),
        ),
        (
            _TS_HIK_COMPACT,
            _format_isapi_dt_hik_compact(start_time),
            _format_isapi_dt_hik_compact(end_time),
        ),
    ]


# ---------------------------------------------------------------------------
# searchType candidates
# ---------------------------------------------------------------------------

# CMR is the configured recording mode on this device.
# Try with CMR first, then without (omitted), then AllEvent.
_SEARCH_TYPES = [
    "CMR",
    "",          # omit searchType element entirely
    "AllEvent",
    "MOTION",
    "ALARM",
    "manual",
]


# ---------------------------------------------------------------------------
# XML schema builders
# Each builder takes (track_id, start_str, end_str, search_type) -> str
# search_type="" means omit the element
# ---------------------------------------------------------------------------

def _st_elem(search_type: str) -> str:
    """Return <searchType>...</searchType> or empty string."""
    if not search_type:
        return ""
    return f"<searchType>{search_type}</searchType>"


def _validate_xml(xml_str: str, label: str) -> bool:
    """Validate XML is well-formed before sending. Returns True if valid."""
    try:
        ET.fromstring(xml_str.split("?>", 1)[-1].strip() if "?>" in xml_str else xml_str)
        return True
    except ET.ParseError as exc:
        logger.error("MALFORMED XML in builder [%s]: %s\nXML: %s", label, exc, xml_str)
        return False


# ---- No-namespace schemas (most likely to work on Hikvision V3.x) ----

def _xml_a1(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """A1: no-NS, trackList + metadataList + maxResults + searchResultPostion + searchType"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '<metadataList>'
        '<metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor>'
        '</metadataList>'
        '</CMSearchDescription>'
    )


def _xml_a2(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """A2: no-NS, trackList + maxResults + searchResultPostion + searchType"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_a3(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """A3: no-NS, trackList only + searchType"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_a4(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """A4: no-NS, searchType BEFORE trackList"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'{_st_elem(st)}'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>'
    )


def _xml_a5(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """A5: no-NS, searchRecordType instead of searchType"""
    st_elem = f"<searchRecordType>{st}</searchRecordType>" if st else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{st_elem}'
        '</CMSearchDescription>'
    )


# ---- Hikvision-namespace schemas ----

def _xml_h1(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """H1: Hikvision NS, trackList + metadataList + maxResults + searchType"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{HIK_NS}">'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '<metadataList>'
        '<metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor>'
        '</metadataList>'
        '</CMSearchDescription>'
    )


def _xml_h2(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """H2: Hikvision NS, trackList + maxResults + searchType"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{HIK_NS}">'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_h3(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """H3: Hikvision NS, trackList only + searchType"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{HIK_NS}">'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_h4(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """H4: Hikvision NS, searchType BEFORE trackList"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{HIK_NS}">'
        '<searchID>1</searchID>'
        f'{_st_elem(st)}'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>'
    )


# ---- Flat time schemas (no timeSpanList wrapper — some NVR firmware variants) ----

def _xml_f1(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """F1: no-NS, startTime/endTime directly under CMSearchDescription (no timeSpanList)"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_f2(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """F2: Hikvision NS, startTime/endTime directly under CMSearchDescription"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{HIK_NS}">'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_f3(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """F3: no-NS, timeSpan directly under CMSearchDescription (no timeSpanList wrapper)"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_f4(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """F4: Hikvision NS, timeSpan directly under CMSearchDescription"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{HIK_NS}">'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_f5(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """F5: no-NS, beginTime/endTime instead of startTime/endTime"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<beginTime>{start_str}</beginTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_f6(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """F6: no-NS, startTime/endTime at top level + no trackList wrapper"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackID>{track_id}</trackID>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


# ---- PSIA-namespace schemas (last resort — device uses PSIA only for errors) ----

def _xml_p1(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """P1: PSIA NS, trackList + maxResults + searchType"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'<maxResults>{MAX_RESULTS}</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


def _xml_p2(track_id: str, start_str: str, end_str: str, st: str) -> str:
    """P2: PSIA NS, trackList only"""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList>'
        f'<trackID>{track_id}</trackID>'
        '</trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{start_str}</startTime>'
        f'<endTime>{end_str}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        f'{_st_elem(st)}'
        '</CMSearchDescription>'
    )


# Schema variant list — (name, builder_fn)
#
# ORDERING RATIONALE (based on "Tag N is invalid (two root tags)" errors):
#   The NVR at 192.168.2.100 rejects <timeSpanList> as an unknown element.
#   It counts XML tags and reports the offending tag number.
#   "Tag 11 is invalid" = <startTime> inside <timeSpanList><timeSpan> is rejected.
#   This means the NVR does NOT use <timeSpanList> — it expects time at a different level.
#
#   F-series schemas (flat time) are tried FIRST:
#     F1/F2: startTime/endTime directly under CMSearchDescription
#     F3/F4: timeSpan directly under CMSearchDescription (no timeSpanList wrapper)
#     F5:    beginTime/endTime instead of startTime/endTime
#     F6:    no trackList wrapper either
#
#   A/H-series (with timeSpanList) are tried after as fallbacks.
_XML_SCHEMA_VARIANTS = [
    # ---- Flat-time schemas (no timeSpanList — most likely for this NVR) ----
    ("F1_no_ns_flat_startTime_endTime", _xml_f1),
    ("F2_hik_ns_flat_startTime_endTime", _xml_f2),
    ("F3_no_ns_timeSpan_no_list", _xml_f3),
    ("F4_hik_ns_timeSpan_no_list", _xml_f4),
    ("F5_no_ns_beginTime_endTime", _xml_f5),
    ("F6_no_ns_no_trackList_wrapper", _xml_f6),
    # ---- Standard schemas with timeSpanList (fallback) ----
    ("A1_no_ns_trackList_metadata_searchType", _xml_a1),
    ("A2_no_ns_trackList_maxResults_searchType", _xml_a2),
    ("A3_no_ns_trackList_only_searchType", _xml_a3),
    ("A4_no_ns_searchType_before_trackList", _xml_a4),
    ("A5_no_ns_searchRecordType", _xml_a5),
    ("H1_hik_ns_trackList_metadata_searchType", _xml_h1),
    ("H2_hik_ns_trackList_maxResults_searchType", _xml_h2),
    ("H3_hik_ns_trackList_only_searchType", _xml_h3),
    ("H4_hik_ns_searchType_before_trackList", _xml_h4),
    ("P1_psia_ns_trackList_maxResults_searchType", _xml_p1),
    ("P2_psia_ns_trackList_only_searchType", _xml_p2),
]


# ---------------------------------------------------------------------------
# NVR capability probe
# ---------------------------------------------------------------------------

async def probe_nvr_capabilities(
    nvr_ip: str,
    http_port: int,
    username: str,
    password: str,
    channel: int,
    use_https: bool = False,
) -> NVRCapabilities:
    """Probe NVR to discover track IDs and recording search types."""
    scheme = "https" if use_https else "http"
    caps = NVRCapabilities()

    async with httpx.AsyncClient(
        auth=httpx.DigestAuth(username, password),
        timeout=httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT,
                              write=10.0, pool=5.0),
        verify=False,
        follow_redirects=True,
    ) as client:
        for endpoint in _PROBE_ENDPOINTS:
            url = f"{scheme}://{nvr_ip}:{http_port}{endpoint}"
            try:
                resp = await client.get(url, headers={"Accept": "application/xml, */*"})
                logger.info("[probe] GET %s → HTTP %d", endpoint, resp.status_code)
                logger.debug("[probe] %s body:\n%s", endpoint, resp.text[:2000])
                caps.raw_probe_responses[endpoint] = resp.text

                # Abort probe immediately if account is locked
                if _is_account_locked(resp.status_code, resp.text):
                    unlock_secs = _extract_unlock_time(resp.text)
                    unlock_msg = f" Unlocks in {unlock_secs}s." if unlock_secs else ""
                    logger.error(
                        "[probe] NVR account LOCKED at %s:%d.%s Aborting.",
                        nvr_ip, http_port, unlock_msg,
                    )
                    raise PlaybackSearchError(
                        f"NVR account LOCKED at {nvr_ip}:{http_port}.{unlock_msg} "
                        f"Wait for lockout to expire before retrying."
                    )

                if resp.is_success and resp.text.strip():
                    _parse_probe_response(endpoint, resp.text, caps)

            except PlaybackSearchError:
                raise
            except Exception as exc:
                logger.warning("[probe] %s failed: %s", endpoint, exc)

    # Build set of connected channel IDs from InputProxy
    connected_channel_ids: set = set()
    for ch in caps.streaming_channels:
        cid = ch.get("id") or ch.get("channelID") or ch.get("channelNo")
        if cid:
            connected_channel_ids.add(str(cid).strip())

    logger.info("[probe] Connected channel IDs from InputProxy: %s", connected_channel_ids)

    # Filter track IDs: only keep tracks that correspond to connected channels
    # Track ID formula: channel_id * 100 + 1  (e.g. ch1 → 101, ch2 → 201)
    # Also accept the raw channel ID as a track ID (some firmware uses ch ID directly)
    if connected_channel_ids:
        valid_track_ids: List[str] = []
        for cid_str in connected_channel_ids:
            try:
                cid_int = int(cid_str)
                # Primary track ID: channel * 100 + 1
                primary = str(cid_int * 100 + 1)
                if primary in caps.track_ids and primary not in valid_track_ids:
                    valid_track_ids.append(primary)
                # Also add raw channel ID if it appears as a track
                if cid_str in caps.track_ids and cid_str not in valid_track_ids:
                    valid_track_ids.append(cid_str)
            except ValueError:
                pass
        if valid_track_ids:
            logger.info(
                "[probe] Filtered track IDs (connected channels only): %s → %s",
                caps.track_ids[:10], valid_track_ids,
            )
            caps.track_ids = valid_track_ids
        else:
            logger.warning(
                "[probe] No track IDs matched connected channels — keeping all: %s",
                caps.track_ids[:10],
            )
    else:
        # No InputProxy data — keep all discovered track IDs but warn
        logger.warning(
            "[probe] No InputProxy channel data — using all discovered track IDs: %s",
            caps.track_ids[:10],
        )

    logger.info(
        "[probe] ch=%d on %s:%d: final_track_ids=%s search_types=%s",
        channel, nvr_ip, http_port,
        caps.track_ids or "(none — using defaults)",
        caps.record_search_types or "(none — using defaults)",
    )
    return caps


def _parse_probe_response(endpoint: str, xml_text: str,
                           caps: NVRCapabilities) -> None:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return

    if "InputProxy/channels" in endpoint:
        _parse_input_proxy_channels(root, caps)
    elif "record/tracks" in endpoint:
        _parse_record_tracks(root, caps)
    elif "deviceInfo" in endpoint:
        _parse_device_info(root, caps)


def _parse_input_proxy_channels(root: ET.Element, caps: NVRCapabilities) -> None:
    for item in root.iter():
        if _strip_ns(item.tag) in ("InputProxyChannel", "channel"):
            ch_info: Dict = {}
            for child in item:
                ctag = _strip_ns(child.tag)
                if ctag in ("id", "channelID", "channelNo"):
                    ch_info[ctag] = (child.text or "").strip()
            if ch_info:
                caps.streaming_channels.append(ch_info)
                logger.debug("[probe] InputProxy channel: %s", ch_info)


def _parse_record_tracks(root: ET.Element, caps: NVRCapabilities) -> None:
    """Extract track IDs and recording modes from /ISAPI/ContentMgmt/record/tracks.

    NOTE: We store ALL track IDs here in a temporary list. After both
    InputProxy/channels and record/tracks are parsed, we cross-reference
    to only keep track IDs that correspond to connected channels.
    This avoids sending invalid trackIDs (e.g. 901, 1001) to the NVR.
    """
    for item in root.iter():
        if _strip_ns(item.tag) == "Track":
            track_id = _find_text(item, "id")
            if track_id and track_id not in caps.track_ids:
                caps.track_ids.append(track_id)
                logger.debug("[probe] Record track ID: %s", track_id)
            # Extract recording mode
            mode = _find_text(item, "DefaultRecordingMode")
            if mode and mode not in caps.record_search_types:
                caps.record_search_types.append(mode)


def _parse_device_info(root: ET.Element, caps: NVRCapabilities) -> None:
    model = _find_text(root, "model")
    fw = _find_text(root, "firmwareVersion")
    if model or fw:
        logger.info("[probe] Device: model=%s firmware=%s", model, fw)


# ---------------------------------------------------------------------------
# ISAPI response helpers
# ---------------------------------------------------------------------------

class _EarlyRtspFallback(Exception):
    """Raised internally to break out of the ISAPI loop and go straight to RTSP probe."""


def _is_bad_xml(status_code: int, body: str) -> bool:
    if status_code != 400:
        return False
    bl = body.lower()
    return (
        "badxmlcontent" in bl
        or "badxmlformat" in bl
        or "invalid xml" in bl
    )


def _is_account_locked(status_code: int, body: str) -> bool:
    """Detect NVR account lockout — stop retrying immediately if locked."""
    if status_code not in (401, 403):
        return False
    bl = body.lower()
    return "lockstatus" in bl and "lock" in bl


def _extract_unlock_time(body: str) -> Optional[int]:
    """Extract unlockTime seconds from NVR lockout response."""
    try:
        root = ET.fromstring(body)
        val = _find_text(root, "unlockTime")
        return int(val) if val and val.isdigit() else None
    except Exception:
        return None


def _parse_search_response(xml_text: str, channel: int) -> List[RecordingSegment]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise PlaybackSearchError(f"Invalid XML in search response: {exc}") from exc

    status_str = (_find_text(root, "responseStatusStrg") or "").upper()
    if status_str and status_str not in ("OK", "MORE", "NO MATCHES"):
        raise PlaybackSearchError(f"Search returned status: {status_str!r}")

    segments: List[RecordingSegment] = []
    for item in root.iter():
        if _strip_ns(item.tag) != "searchMatchItem":
            continue
        start_str = end_str = None
        recording_type = "normal"
        for child in item.iter():
            tag = _strip_ns(child.tag)
            if tag == "startTime":
                start_str = (child.text or "").strip()
            elif tag == "endTime":
                end_str = (child.text or "").strip()
            elif tag == "recordType":
                recording_type = (child.text or "normal").strip().lower()
        if not start_str or not end_str:
            continue
        start_dt = _parse_hikvision_datetime(start_str)
        end_dt = _parse_hikvision_datetime(end_str)
        if start_dt is None or end_dt is None:
            logger.warning("Skipping segment with unparseable times: %r / %r",
                           start_str, end_str)
            continue
        segments.append(RecordingSegment(
            start=start_dt, end=end_dt,
            track_id=str(channel_to_track_id(channel)),
            recording_type=recording_type,
        ))
    logger.debug("Parsed %d segments for ch=%d", len(segments), channel)
    return segments


# ---------------------------------------------------------------------------
# Single search POST
# ---------------------------------------------------------------------------

async def _post_search(
    client: httpx.AsyncClient,
    url: str,
    xml_body: str,
    label: str,
) -> Tuple[int, str]:
    logger.info("[%s] POST %s", label, url)
    logger.debug("[%s] XML:\n%s", label, xml_body)

    response = await client.post(
        url,
        content=xml_body.encode("utf-8"),
        headers={
            "Content-Type": "application/xml",
            "Accept": "application/xml, text/xml, */*",
        },
    )
    logger.debug(
        "[%s] HTTP %d\nBody:\n%s",
        label, response.status_code, response.text[:2000],
    )
    return response.status_code, response.text


# ---------------------------------------------------------------------------
# RTSP probe fallback
# Used when the NVR firmware rejects all ISAPI search XML formats.
# Probes time windows via RTSP DESCRIBE to detect recording presence.
# Confirmed working on DS-7616NI-Q1 V3.4.104 where ISAPI search is broken.
# ---------------------------------------------------------------------------

async def _probe_rtsp_segment(
    rtsp_host: str,
    rtsp_port: int,
    username: str,
    password: str,
    track_id: int,
    start: datetime,
    end: datetime,
) -> bool:
    """Return True if RTSP DESCRIBE confirms a recording exists for this window."""
    start_str = _format_rtsp_dt(start)
    end_str   = _format_rtsp_dt(end)
    uri       = f"/Streaming/tracks/{track_id}?starttime={start_str}&endtime={end_str}"
    rtsp_url  = f"rtsp://{rtsp_host}:{rtsp_port}{uri}"

    async def _recv_headers(reader: asyncio.StreamReader) -> str:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=8.0)
            if not chunk:
                break
            data += chunk
        return data.decode(errors="replace")

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(rtsp_host, rtsp_port), timeout=8.0
        )
        try:
            req = (
                f"DESCRIBE {rtsp_url} RTSP/1.0\r\n"
                f"CSeq: 1\r\nAccept: application/sdp\r\n\r\n"
            )
            writer.write(req.encode())
            await writer.drain()
            resp = await _recv_headers(reader)

            if "200 OK" in resp:
                return True

            if "401" in resp:
                realm_m = re.search(r'realm="([^"]+)"', resp)
                nonce_m = re.search(r'nonce="([^"]+)"', resp)
                if realm_m and nonce_m:
                    ha1 = hashlib.md5(
                        f"{username}:{realm_m.group(1)}:{password}".encode()
                    ).hexdigest()
                    ha2 = hashlib.md5(f"DESCRIBE:{uri}".encode()).hexdigest()
                    digest_resp = hashlib.md5(
                        f"{ha1}:{nonce_m.group(1)}:{ha2}".encode()
                    ).hexdigest()
                    auth = (
                        f'Digest username="{username}", '
                        f'realm="{realm_m.group(1)}", '
                        f'nonce="{nonce_m.group(1)}", '
                        f'uri="{uri}", response="{digest_resp}"'
                    )
                    req2 = (
                        f"DESCRIBE {rtsp_url} RTSP/1.0\r\n"
                        f"CSeq: 2\r\nAccept: application/sdp\r\n"
                        f"Authorization: {auth}\r\n\r\n"
                    )
                    writer.write(req2.encode())
                    await writer.drain()
                    resp2 = await _recv_headers(reader)
                    return "200 OK" in resp2
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    except Exception as exc:
        logger.debug("[RTSP probe] %s: %s", uri, exc)

    return False


def _merge_segments(segments: List[RecordingSegment]) -> List[RecordingSegment]:
    """Merge adjacent recording segments produced by the RTSP probe."""
    if not segments:
        return []
    merged = [segments[0]]
    for seg in segments[1:]:
        last = merged[-1]
        if seg.start <= last.end:
            merged[-1] = RecordingSegment(
                start=last.start,
                end=max(last.end, seg.end),
                track_id=last.track_id,
                recording_type=last.recording_type,
            )
        else:
            merged.append(seg)
    return merged


async def _search_via_rtsp_probe(
    nvr_ip: str,
    rtsp_port: int,
    username: str,
    password: str,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> List[RecordingSegment]:
    """
    Probe RTSP DESCRIBE for recording presence when ISAPI search is unsupported.

    Divides the requested window into probe intervals and checks each one.
    Returns coarse RecordingSegment objects suitable for timeline display.
    """
    track_id = channel_to_track_id(channel)
    total_secs = (end_time - start_time).total_seconds()

    if total_secs <= 3600:
        interval = timedelta(minutes=15)
    elif total_secs <= 14400:
        interval = timedelta(minutes=30)
    else:
        interval = timedelta(hours=1)

    logger.info(
        "[RTSP probe] ch=%d track=%d  %s -> %s  interval=%s",
        channel, track_id,
        _format_isapi_dt_utc_z(start_time),
        _format_isapi_dt_utc_z(end_time),
        interval,
    )

    segments: List[RecordingSegment] = []
    current = start_time
    while current < end_time:
        probe_end = min(current + interval, end_time)
        if await _probe_rtsp_segment(
            nvr_ip, rtsp_port, username, password, track_id, current, probe_end
        ):
            segments.append(RecordingSegment(
                start=current,
                end=probe_end,
                track_id=str(track_id),
                recording_type="normal",
            ))
        current = probe_end

    merged = _merge_segments(segments)
    logger.info(
        "[RTSP probe] ch=%d  found %d segment(s)  (from %d probes)",
        channel, len(merged), int(total_secs / interval.total_seconds()),
    )
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_recordings(
    nvr_ip: str,
    http_port: int,
    username: str,
    password: str,
    channel: int,
    start_time: datetime,
    end_time: datetime,
    use_https: bool = False,
    rtsp_port: int = 554,
    nvr_timezone: str = "WIB",
) -> List[RecordingSegment]:
    """
    Search for recording segments on a Hikvision NVR via ISAPI.

    Search matrix (ordered by likelihood of success for DS-7616NI-Q1 V3.4.x):
      endpoint × track_id × timestamp_format × search_type × xml_schema

    Stops on first successful response.
    Aborts immediately on account lockout.
    """
    scheme = "https" if use_https else "http"

    logger.info(
        "Recording search: %s:%d ch=%d %s → %s",
        nvr_ip, http_port, channel,
        _format_isapi_dt_utc_z(start_time),
        _format_isapi_dt_utc_z(end_time),
    )

    # Step 1: Probe NVR (safe GET requests only)
    try:
        caps = await probe_nvr_capabilities(
            nvr_ip, http_port, username, password, channel, use_https,
        )
    except PlaybackSearchError:
        raise
    except Exception as exc:
        logger.warning("NVR probe failed (using defaults): %s", exc)
        caps = NVRCapabilities()

    # Step 2: Build candidate lists
    track_ids = _track_id_candidates(channel, caps.track_ids)
    ts_candidates = _timestamp_candidates(start_time, end_time, nvr_timezone)

    # Build searchType list — use discovered recording modes first
    search_types = list(_SEARCH_TYPES)
    if caps.record_search_types:
        # Prepend discovered types (dedup)
        for st in reversed(caps.record_search_types):
            if st not in search_types:
                search_types.insert(0, st)
            else:
                # Move to front
                search_types.remove(st)
                search_types.insert(0, st)

    total = (
        len(_SEARCH_ENDPOINTS)
        * len(track_ids)
        * len(ts_candidates)
        * len(search_types)
        * len(_XML_SCHEMA_VARIANTS)
    )
    logger.info(
        "Search matrix: endpoints=%s track_ids=%s ts_modes=%d "
        "search_types=%s schemas=%d total=%d",
        _SEARCH_ENDPOINTS, track_ids,
        len(ts_candidates),
        search_types,
        len(_XML_SCHEMA_VARIANTS),
        total,
    )

    last_error: Optional[str] = None
    attempts = 0
    bad_xml_count = 0

    try:
        async with httpx.AsyncClient(
            auth=httpx.DigestAuth(username, password),
            timeout=httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT,
                                  write=10.0, pool=5.0),
            verify=False,
            follow_redirects=True,
        ) as client:

            for endpoint in _SEARCH_ENDPOINTS:
                url = f"{scheme}://{nvr_ip}:{http_port}{endpoint}"
                logger.info("--- Endpoint: %s ---", endpoint)

                for track_id in track_ids:
                    logger.info("  trackID=%s", track_id)

                    for ts_mode, start_str, end_str in ts_candidates:
                        logger.info(
                            "    ts=%s  start=%s  end=%s",
                            ts_mode, start_str, end_str,
                        )

                        for search_type in search_types:
                            st_label = f"st={search_type!r}" if search_type else "st=<omit>"

                            for schema_name, builder_fn in _XML_SCHEMA_VARIANTS:
                                label = (
                                    f"trackID={track_id} ts={ts_mode} "
                                    f"{st_label} {schema_name}"
                                )
                                xml_body = builder_fn(
                                    track_id, start_str, end_str, search_type
                                )
                                attempts += 1

                                try:
                                    status_code, body = await _post_search(
                                        client, url, xml_body, label,
                                    )
                                except httpx.TimeoutException as exc:
                                    raise PlaybackSearchError(
                                        f"Timeout on {nvr_ip}:{http_port}: {exc}"
                                    ) from exc
                                except httpx.ConnectError as exc:
                                    raise PlaybackSearchError(
                                        f"Cannot connect to {nvr_ip}:{http_port}: {exc}"
                                    ) from exc
                                except httpx.RequestError as exc:
                                    raise PlaybackSearchError(
                                        f"Network error: {exc}"
                                    ) from exc

                                # Account locked — abort immediately
                                if _is_account_locked(status_code, body):
                                    unlock_secs = _extract_unlock_time(body)
                                    unlock_msg = (
                                        f" Account unlocks in {unlock_secs}s."
                                        if unlock_secs else ""
                                    )
                                    raise PlaybackSearchError(
                                        f"NVR account LOCKED at {nvr_ip}:{http_port} "
                                        f"(HTTP {status_code}).{unlock_msg} "
                                        f"Wait for lockout to expire before retrying."
                                    )

                                # Auth failure — abort
                                if status_code in (401, 403):
                                    raise PlaybackSearchError(
                                        f"Authentication failed for {nvr_ip}:{http_port} "
                                        f"(HTTP {status_code})"
                                    )

                                # 404 — endpoint dead, skip all remaining
                                if status_code == 404:
                                    logger.warning(
                                        "[%s] HTTP 404 — endpoint not found", label,
                                    )
                                    last_error = f"[{label}] HTTP 404"
                                    raise PlaybackSearchError(
                                        f"Search endpoint not found: {endpoint}"
                                    )

                                # Bad XML — try next combination
                                if _is_bad_xml(status_code, body):
                                    logger.warning(
                                        "[%s] HTTP %d badXml — next\nXML: %s\nResp: %s",
                                        label, status_code,
                                        xml_body[:300], body[:300],
                                    )
                                    last_error = f"[{label}] badXml: {body[:150]}"
                                    bad_xml_count += 1
                                    # Early exit: firmware clearly rejects all XML —
                                    # skip remaining combos and go straight to RTSP probe.
                                    if bad_xml_count >= 5:
                                        logger.warning(
                                            "%d consecutive badXmlContent responses — "
                                            "firmware does not support ISAPI search. "
                                            "Aborting remaining combos, falling back to RTSP probe.",
                                            bad_xml_count,
                                        )
                                        raise _EarlyRtspFallback()
                                    continue

                                # Other 4xx/5xx — try next
                                if status_code >= 400:
                                    logger.warning(
                                        "[%s] HTTP %d — next\nBody: %s",
                                        label, status_code, body[:300],
                                    )
                                    last_error = (
                                        f"[{label}] HTTP {status_code}: {body[:150]}"
                                    )
                                    continue

                                # ---- SUCCESS ----
                                logger.info(
                                    "=== SUCCESS: [%s] after %d attempt(s) "
                                    "— HTTP %d from %s:%d ===",
                                    label, attempts, status_code, nvr_ip, http_port,
                                )
                                logger.info("Successful XML body:\n%s", xml_body)

                                if not body.strip():
                                    logger.info("[%s] Empty body — no recordings", label)
                                    return []

                                segments = _parse_search_response(body, channel)
                                segments.sort(key=lambda s: s.start)
                                logger.info(
                                    "[%s] Found %d segment(s) for ch=%d",
                                    label, len(segments), channel,
                                )
                                return segments

    except _EarlyRtspFallback:
        pass  # handled below — fall through to RTSP probe
    except PlaybackSearchError:
        raise
    except Exception as exc:
        raise PlaybackSearchError(
            f"Unexpected error searching {nvr_ip}:{http_port}: {exc}"
        ) from exc
    else:
        # Normal exhaustion path: only fall back if every attempt was badXml.
        if not (bad_xml_count > 0 and bad_xml_count == attempts):
            raise PlaybackSearchError(
                f"All {attempts} combinations rejected by {nvr_ip}:{http_port}. "
                f"Last error: {last_error}"
            )

    # All combinations returned badXmlContent (or early-exit triggered).
    # The firmware has a broken ISAPI search parser (confirmed DS-7616NI-Q1 V3.4.104).
    # Fall back to RTSP DESCRIBE probing to build a coarse recording timeline.
    if bad_xml_count > 0:
        logger.warning(
            "All %d ISAPI search attempts returned badXmlContent — "
            "firmware does not support ISAPI search. "
            "Falling back to RTSP probe for ch=%d on %s:%d.",
            attempts, channel, nvr_ip, rtsp_port,
        )
        try:
            return await _search_via_rtsp_probe(
                nvr_ip, rtsp_port, username, password, channel, start_time, end_time,
            )
        except Exception as exc:
            logger.error("RTSP probe fallback failed: %s", exc)
            raise PlaybackSearchError(
                f"ISAPI search unsupported and RTSP probe failed: {exc}"
            ) from exc


def build_playback_rtsp_url(
    nvr_ip: str,
    rtsp_port: int,
    username: str,
    password: str,
    channel: int,
    start_time: datetime,
    end_time: datetime,
) -> str:
    """
    Build an authenticated Hikvision RTSP playback URL.
    This URL must NEVER be sent to the frontend — only passed to go2rtc.
    """
    track_id = channel_to_track_id(channel)
    start_str = _format_rtsp_dt(start_time)
    end_str = _format_rtsp_dt(end_time)

    enc_user = quote(username, safe="")
    enc_pass = quote(password, safe="")

    url = (
        f"rtsp://{enc_user}:{enc_pass}@{nvr_ip}:{rtsp_port}"
        f"/Streaming/tracks/{track_id}"
        f"?starttime={start_str}&endtime={end_str}"
    )

    logger.debug(
        "Built playback RTSP: rtsp://***:***@%s:%d/Streaming/tracks/%d"
        "?starttime=%s&endtime=%s",
        nvr_ip, rtsp_port, track_id, start_str, end_str,
    )
    return url
