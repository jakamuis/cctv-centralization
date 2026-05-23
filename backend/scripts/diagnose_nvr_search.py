#!/usr/bin/env python3
"""
diagnose_nvr_search.py

Standalone NVR recording search diagnostic tool.

IMPORTANT: Run this from INSIDE the backend Docker container so it can
reach the NVR on the internal Docker network:

    docker exec -it cctv_backend python /app/scripts/diagnose_nvr_search.py \
        --ip 192.168.152.101 \
        --port 80 \
        --user admin \
        --pass yourpassword \
        --channel 1

DO NOT run from the host machine — the NVR is on the Docker internal
network and is not reachable from the host.

The script will:
  1. Test basic connectivity (GET /ISAPI/System/deviceInfo)
  2. Probe all known streaming/channel endpoints (full response printed)
  3. Try every XML body × Content-Type combination
  4. Print FULL request XML and full NVR response for each attempt
  5. Summarize which combination succeeded

This script uses only stdlib + httpx (already in requirements.txt).
"""

import argparse
import sys
import textwrap
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PSIA_NS = "urn:psialliance-org"
HIK_NS = "http://www.hikvision.com/ver20/XMLSchema"

# Use a fixed 24-hour window ending now
_NOW = datetime.now(timezone.utc)
_START = _NOW.replace(hour=0, minute=0, second=0, microsecond=0)
_END = _NOW.replace(hour=23, minute=59, second=0, microsecond=0)

START_UTC_Z = _START.strftime("%Y-%m-%dT%H:%M:%SZ")
END_UTC_Z = _END.strftime("%Y-%m-%dT%H:%M:%SZ")
START_LOCAL = datetime.fromtimestamp(_START.timestamp()).strftime("%Y-%m-%dT%H:%M:%S")
END_LOCAL = datetime.fromtimestamp(_END.timestamp()).strftime("%Y-%m-%dT%H:%M:%S")

# ---------------------------------------------------------------------------
# Probe endpoints
# ---------------------------------------------------------------------------

PROBE_ENDPOINTS = [
    ("GET", "/ISAPI/System/deviceInfo"),
    ("GET", "/ISAPI/Streaming/channels"),
    ("GET", "/PSIA/Streaming/channels"),
    ("GET", "/ISAPI/ContentMgmt/InputProxy/channels"),
    ("GET", "/ISAPI/System/capabilities"),
    ("GET", "/ISAPI/ContentMgmt/record/tracks"),
    ("GET", "/PSIA/ContentMgmt/record/tracks"),
]

# ---------------------------------------------------------------------------
# Search XML bodies to test
# (track_id placeholder = {TID}, start = {S}, end = {E})
# ---------------------------------------------------------------------------

SEARCH_BODIES = [
    # ---- PSIA namespace variants ----
    (
        "PSIA_P1_trackList_maxResults",
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '<maxResults>200</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>',
    ),
    (
        "PSIA_P2_trackList_only",
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '</CMSearchDescription>',
    ),
    (
        "PSIA_P3_no_searchID_trackList",
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '</CMSearchDescription>',
    ),
    (
        "PSIA_P4_version_attr_trackList",
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription version="1.0" xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '<maxResults>200</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>',
    ),
    (
        "PSIA_P5_searchResultPosition_correct_spelling",
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '<maxResults>200</maxResults>'
        '<searchResultPosition>0</searchResultPosition>'
        '</CMSearchDescription>',
    ),
    (
        "PSIA_P6_pure_minimal_no_searchID_no_maxResults",
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '</CMSearchDescription>',
    ),
    # ---- No namespace variants ----
    (
        "NO_NS_B1_trackList_maxResults",
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '<maxResults>200</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>',
    ),
    (
        "NO_NS_B2_trackList_only",
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '</CMSearchDescription>',
    ),
    # ---- Hikvision namespace variants ----
    (
        "HIK_NS_F1_trackList_maxResults",
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<CMSearchDescription xmlns="{HIK_NS}">'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '<maxResults>200</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>',
    ),
    # ---- No XML declaration variants (some firmware rejects the <?xml?> header) ----
    (
        "PSIA_NO_DECL_trackList_maxResults",
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '<maxResults>200</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>',
    ),
    (
        "PSIA_NO_DECL_trackList_only",
        f'<CMSearchDescription xmlns="{PSIA_NS}">'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '</CMSearchDescription>',
    ),
    (
        "NO_NS_NO_DECL_trackList_maxResults",
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        '<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList><timeSpan>'
        '<startTime>{S}</startTime><endTime>{E}</endTime>'
        '</timeSpan></timeSpanList>'
        '<maxResults>200</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>',
    ),
]

# Content-Type variants to try for each body
CONTENT_TYPES = [
    "application/xml",
    "text/xml",
    "text/xml; charset=utf-8",
    "application/xml; charset=utf-8",
]

SEARCH_ENDPOINTS = [
    "/ISAPI/ContentMgmt/search",
    "/PSIA/ContentMgmt/search",
]

TRACK_IDS = []  # filled dynamically from channel arg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sep(title: str = "") -> None:
    line = "=" * 70
    if title:
        print(f"\n{line}")
        print(f"  {title}")
        print(line)
    else:
        print(line)


def _print_response(resp: httpx.Response) -> None:
    print(f"  HTTP {resp.status_code}")
    for k, v in resp.headers.items():
        if k.lower() in ("content-type", "content-length", "www-authenticate"):
            print(f"  {k}: {v}")
    body = resp.text
    if body:
        print("  Body (first 2000 chars):")
        print(textwrap.indent(body[:2000], "    "))
    else:
        print("  Body: (empty)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="NVR recording search diagnostic")
    parser.add_argument("--ip",      required=True,  help="NVR IP address")
    parser.add_argument("--port",    default=80,      type=int, help="HTTP port")
    parser.add_argument("--user",    required=True,  help="Username")
    parser.add_argument("--pass",    dest="password", required=True, help="Password")
    parser.add_argument("--channel", default=1,       type=int, help="Channel number")
    parser.add_argument("--https",   action="store_true", help="Use HTTPS")
    parser.add_argument("--fast",    action="store_true",
                        help="Only try application/xml Content-Type (faster)")
    args = parser.parse_args()

    scheme = "https" if args.https else "http"
    base = f"{scheme}://{args.ip}:{args.port}"
    channel = args.channel

    # Build track ID candidates
    track_ids = [
        str(channel * 100 + 1),   # 101
        str(channel),              # 1
        f"{channel}-1",            # 1-1
    ]

    print(f"\nNVR Diagnostic Tool")
    print(f"Target: {base}")
    print(f"Channel: {channel}")
    print(f"Track ID candidates: {track_ids}")
    print(f"Time window (UTC_Z): {START_UTC_Z} → {END_UTC_Z}")
    print(f"Time window (LOCAL):  {START_LOCAL} → {END_LOCAL}")

    auth = httpx.DigestAuth(args.user, args.password)
    client = httpx.Client(
        auth=auth,
        timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
        verify=False,
        follow_redirects=True,
    )

    # -----------------------------------------------------------------------
    # Phase 1: Probe endpoints
    # -----------------------------------------------------------------------
    _sep("PHASE 1: PROBE ENDPOINTS")
    discovered_track_ids = []

    for method, endpoint in PROBE_ENDPOINTS:
        url = f"{base}{endpoint}"
        print(f"\n  {method} {url}")
        try:
            resp = client.request(method, url, headers={"Accept": "application/xml, */*"})
            _print_response(resp)

            # Try to extract track IDs from response
            if resp.is_success and resp.text:
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(resp.text)
                    for elem in root.iter():
                        tag = elem.tag.split("}", 1)[-1] if "}" in elem.tag else elem.tag
                        if tag in ("id", "channelID", "trackID", "channelNo"):
                            val = (elem.text or "").strip()
                            if val and val not in discovered_track_ids:
                                discovered_track_ids.append(val)
                                print(f"  >>> Discovered ID: {val!r} (from <{tag}>)")
                except Exception:
                    pass

        except Exception as exc:
            print(f"  ERROR: {exc}")

    if discovered_track_ids:
        print(f"\n  Discovered IDs from probe: {discovered_track_ids}")
        # Prepend discovered IDs to track_ids (dedup)
        for tid in reversed(discovered_track_ids):
            if tid not in track_ids:
                track_ids.insert(0, tid)
        print(f"  Updated track ID candidates: {track_ids}")

    # -----------------------------------------------------------------------
    # Phase 2: Search attempts
    # -----------------------------------------------------------------------
    _sep("PHASE 2: SEARCH ATTEMPTS")

    success_count = 0
    attempt_count = 0

    # Content-Type list: --fast uses only application/xml
    content_types = ["application/xml"] if args.fast else CONTENT_TYPES

    total_expected = (
        len(SEARCH_ENDPOINTS) * len(track_ids) * 2
        * len(SEARCH_BODIES) * len(content_types)
    )
    print(f"\nTotal combinations to try: {total_expected}")
    print(f"Content-Types: {content_types}")

    for endpoint in SEARCH_ENDPOINTS:
        url = f"{base}{endpoint}"
        _sep(f"Endpoint: {endpoint}")

        for track_id in track_ids:
            for ts_mode, start_str, end_str in [
                ("UTC_Z", START_UTC_Z, END_UTC_Z),
                ("LOCAL_NO_TZ", START_LOCAL, END_LOCAL),
            ]:
                for body_name, body_template in SEARCH_BODIES:
                    xml_body = (
                        body_template
                        .replace("{TID}", track_id)
                        .replace("{S}", start_str)
                        .replace("{E}", end_str)
                    )

                    for ct in content_types:
                        label = f"trackID={track_id} ts={ts_mode} ct={ct!r} {body_name}"
                        attempt_count += 1

                        print(f"\n[{attempt_count}/{total_expected}] {label}")
                        print(f"  POST {url}")
                        print(f"  Content-Type: {ct}")
                        print(f"  XML: {xml_body[:300]}")

                        try:
                            resp = client.post(
                                url,
                                content=xml_body.encode("utf-8"),
                                headers={
                                    "Content-Type": ct,
                                    "Accept": "application/xml, text/xml, */*",
                                },
                            )
                            _print_response(resp)

                            if resp.status_code == 200:
                                print(f"\n  *** SUCCESS: {label} ***")
                                success_count += 1
                                print("  Full response body:")
                                print(textwrap.indent(resp.text, "    "))

                        except Exception as exc:
                            print(f"  ERROR: {exc}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    _sep("SUMMARY")
    print(f"Total attempts: {attempt_count}")
    print(f"Successes: {success_count}")
    if success_count == 0:
        print("\nAll attempts failed with badXmlContent.")
        print("This may indicate:")
        print("  1. The NVR firmware does not support ISAPI/ContentMgmt/search")
        print("  2. The NVR requires a specific Content-Type (try text/xml)")
        print("  3. The NVR requires a specific Accept header")
        print("  4. The NVR uses a completely different search API")
        print("  5. Recording search is disabled in NVR settings")
        print("\nNext steps:")
        print("  - Check NVR web UI for recording search capability")
        print("  - Check NVR firmware version")
        print("  - Try: curl -v --digest -u user:pass \\")
        print(f"      http://{args.ip}:{args.port}/ISAPI/System/deviceInfo")

    client.close()


if __name__ == "__main__":
    main()
