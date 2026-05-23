#!/usr/bin/env python3
"""
probe_nvr_info.py

Quick NVR information probe — prints full responses from key endpoints.
Run this FIRST to identify the device model, firmware, and available APIs.

Usage (from inside Docker container):
    docker exec -it cctv_backend python /app/scripts/probe_nvr_info.py \
        --ip 192.168.152.101 \
        --port 80 \
        --user anekagasmedan \
        --pass 'anekagas#2017'

This script prints EVERYTHING — device info, capabilities, channel list,
recording tracks, and tries alternative search API paths.
"""

import argparse
import sys
import textwrap

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed.")
    sys.exit(1)

# All endpoints to probe
ENDPOINTS = [
    # Device identification
    ("GET",  "/ISAPI/System/deviceInfo"),
    ("GET",  "/PSIA/System/deviceInfo"),
    # Streaming channels
    ("GET",  "/ISAPI/Streaming/channels"),
    ("GET",  "/PSIA/Streaming/channels"),
    # Recording tracks
    ("GET",  "/ISAPI/ContentMgmt/record/tracks"),
    ("GET",  "/PSIA/ContentMgmt/record/tracks"),
    # Input proxy (NVR channels)
    ("GET",  "/ISAPI/ContentMgmt/InputProxy/channels"),
    ("GET",  "/PSIA/ContentMgmt/InputProxy/channels"),
    # Capabilities
    ("GET",  "/ISAPI/System/capabilities"),
    ("GET",  "/PSIA/System/capabilities"),
    # Storage
    ("GET",  "/ISAPI/ContentMgmt/Storage"),
    ("GET",  "/PSIA/ContentMgmt/Storage"),
    # Recording schedule (confirms recording is configured)
    ("GET",  "/ISAPI/ContentMgmt/record/tracks/101"),
    ("GET",  "/ISAPI/ContentMgmt/record/tracks/1"),
    # Search capability
    ("GET",  "/ISAPI/ContentMgmt/search/capabilities"),
    ("GET",  "/PSIA/ContentMgmt/search/capabilities"),
    # Alternative search endpoints (some firmware uses different paths)
    ("GET",  "/ISAPI/ContentMgmt/logSearch"),
    ("GET",  "/ISAPI/ContentMgmt/search"),
    ("GET",  "/PSIA/ContentMgmt/search"),
]

# Minimal POST bodies to test alternative search paths
# These use the absolute simplest possible XML
SEARCH_PROBES = [
    # Try GET on search endpoint (some firmware supports GET with params)
    ("GET",  "/ISAPI/ContentMgmt/search?trackID=101&startTime=2026-05-23T00:00:00Z&endTime=2026-05-23T23:59:59Z"),
    ("GET",  "/ISAPI/ContentMgmt/search?channel=1&startTime=2026-05-23T00:00:00Z&endTime=2026-05-23T23:59:59Z"),
    # Alternative recording search paths
    ("GET",  "/ISAPI/ContentMgmt/record/search"),
    ("GET",  "/PSIA/ContentMgmt/record/search"),
    ("GET",  "/ISAPI/ContentMgmt/playback"),
    ("GET",  "/ISAPI/ContentMgmt/playback/tracks"),
    ("GET",  "/ISAPI/ContentMgmt/playback/tracks/101"),
]


def _sep(title: str = "") -> None:
    line = "=" * 70
    if title:
        print(f"\n{line}")
        print(f"  {title}")
        print(line)
    else:
        print(line)


def _print_full(resp: httpx.Response, endpoint: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {resp.request.method} {endpoint}")
    print(f"  HTTP {resp.status_code}")
    for k, v in resp.headers.items():
        if k.lower() in ("content-type", "content-length", "server", "www-authenticate"):
            print(f"  {k}: {v}")
    body = resp.text
    if body:
        print(f"  Body ({len(body)} bytes):")
        print(textwrap.indent(body[:5000], "    "))
        if len(body) > 5000:
            print(f"    ... (truncated, {len(body)} total bytes)")
    else:
        print("  Body: (empty)")


def main() -> None:
    parser = argparse.ArgumentParser(description="NVR information probe")
    parser.add_argument("--ip",   required=True)
    parser.add_argument("--port", default=80, type=int)
    parser.add_argument("--user", required=True)
    parser.add_argument("--pass", dest="password", required=True)
    parser.add_argument("--https", action="store_true")
    args = parser.parse_args()

    scheme = "https" if args.https else "http"
    base = f"{scheme}://{args.ip}:{args.port}"

    print(f"\nNVR Information Probe")
    print(f"Target: {base}")
    print(f"User: {args.user}")

    client = httpx.Client(
        auth=httpx.DigestAuth(args.user, args.password),
        timeout=httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=5.0),
        verify=False,
        follow_redirects=True,
    )

    _sep("PHASE 1: DEVICE IDENTIFICATION AND CAPABILITIES")
    for method, endpoint in ENDPOINTS:
        url = f"{base}{endpoint}"
        try:
            resp = client.request(
                method, url,
                headers={"Accept": "application/xml, text/xml, */*"},
            )
            _print_full(resp, endpoint)
        except Exception as exc:
            print(f"\n  {method} {endpoint}")
            print(f"  ERROR: {exc}")

    _sep("PHASE 2: ALTERNATIVE SEARCH API PATHS")
    for method, endpoint in SEARCH_PROBES:
        url = f"{base}{endpoint}"
        try:
            resp = client.request(
                method, url,
                headers={"Accept": "application/xml, text/xml, */*"},
            )
            _print_full(resp, endpoint)
        except Exception as exc:
            print(f"\n  {method} {endpoint}")
            print(f"  ERROR: {exc}")

    _sep("DONE")
    print("Review the output above to identify:")
    print("  1. Device model and firmware version (from deviceInfo)")
    print("  2. Available recording tracks (from record/tracks)")
    print("  3. Which endpoints return 200 vs 404 vs 400")
    print("  4. Any alternative search API paths")

    client.close()


if __name__ == "__main__":
    main()
