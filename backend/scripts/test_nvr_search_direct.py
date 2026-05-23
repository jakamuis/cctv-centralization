#!/usr/bin/env python3
"""
test_nvr_search_direct.py

ANALYSIS OF INCONSISTENT RESULTS:
  The NVR gives different responses to the SAME XML body on different runs.
  This suggests:
  1. The NVR has session state that affects XML parsing
  2. The NVR has rate limiting that starts rejecting after many requests
  3. The NVR's XML parser is stateful (previous request affects next)

NEW STRATEGY:
  - Send ONLY ONE request per run
  - Wait between requests
  - Use a fresh HTTP connection each time
  - Try the EXACT XML that the iVMS client sends

The iVMS client uses a specific XML format. Let's try to replicate it exactly.
Based on Hikvision ISAPI documentation for DS-7616NI-Q1:

The correct format for this NVR model may be:
  <CMSearchDescription>
    <searchID>UUID</searchID>  ← UUID not integer!
    <trackList>
      <trackID>101</trackID>  ← trackID not id!
    </trackList>
    <timeSpanList>
      <timeSpan>
        <startTime>ISO_Z</startTime>
        <endTime>ISO_Z</endTime>
      </timeSpan>
    </timeSpanList>
    <maxResults>40</maxResults>
    <searchResultPostion>0</searchResultPostion>
    <metadataList>
      <metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor>
    </metadataList>
  </CMSearchDescription>

Usage:
  docker exec -it cctv_backend python /app/scripts/test_nvr_search_direct.py \
    --ip 192.168.2.100 --port 80 \
    --user admin --pass 'password' \
    --test N  (1-10, default=1)
"""

import argparse
import asyncio
import sys
import uuid
import xml.etree.ElementTree as ET

import httpx

URL_PATH = "/ISAPI/ContentMgmt/search"

# Confirmed valid timestamps (from NVR UI, local time)
START_Z = "2026-05-22T09:17:13Z"
END_Z = "2026-05-22T10:30:50Z"
TID = "101"


def make_v1_simple():
    """Original confirmed structure."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        f'<startTime>{START_Z}</startTime>'
        f'<stopTime>{END_Z}</stopTime>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>CMR</searchType>'
        '</CMSearchDescription>'
    )


def make_v2_trackid():
    """Use <trackID> instead of <id>."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><trackID>{TID}</trackID></trackList>'
        f'<startTime>{START_Z}</startTime>'
        f'<stopTime>{END_Z}</stopTime>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>CMR</searchType>'
        '</CMSearchDescription>'
    )


def make_v3_timespan():
    """Use <timeSpanList><timeSpan> structure."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{START_Z}</startTime>'
        f'<endTime>{END_Z}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>CMR</searchType>'
        '</CMSearchDescription>'
    )


def make_v4_timespan_trackid():
    """Use <timeSpanList> + <trackID>."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><trackID>{TID}</trackID></trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{START_Z}</startTime>'
        f'<endTime>{END_Z}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>CMR</searchType>'
        '</CMSearchDescription>'
    )


def make_v5_metadata():
    """Use metadataList (newer ISAPI format)."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        f'<searchID>{uuid.uuid4()}</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{START_Z}</startTime>'
        f'<endTime>{END_Z}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<metadataList>'
        '<metadataDescriptor>//recordType.meta.std-cgi.com</metadataDescriptor>'
        '</metadataList>'
        '</CMSearchDescription>'
    )


def make_v6_uuid_simple():
    """UUID searchID + simple structure."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        f'<searchID>{uuid.uuid4()}</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        f'<startTime>{START_Z}</startTime>'
        f'<stopTime>{END_Z}</stopTime>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>CMR</searchType>'
        '</CMSearchDescription>'
    )


def make_v7_allEvent_timespan():
    """AllEvent + timeSpanList."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{START_Z}</startTime>'
        f'<endTime>{END_Z}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>AllEvent</searchType>'
        '</CMSearchDescription>'
    )


def make_v8_no_searchtype_timespan():
    """No searchType + timeSpanList."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        f'<startTime>{START_Z}</startTime>'
        f'<endTime>{END_Z}</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '</CMSearchDescription>'
    )


def make_v9_endtime_simple():
    """Use <endTime> instead of <stopTime>."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        f'<startTime>{START_Z}</startTime>'
        f'<endTime>{END_Z}</endTime>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>CMR</searchType>'
        '</CMSearchDescription>'
    )


def make_v10_wide_timespan():
    """Wide range + timeSpanList."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CMSearchDescription>'
        '<searchID>1</searchID>'
        f'<trackList><id>{TID}</id></trackList>'
        '<timeSpanList>'
        '<timeSpan>'
        '<startTime>2026-05-22T09:17:13Z</startTime>'
        '<endTime>2026-05-22T23:59:59Z</endTime>'
        '</timeSpan>'
        '</timeSpanList>'
        '<maxResults>40</maxResults>'
        '<searchResultPostion>0</searchResultPostion>'
        '<searchType>CMR</searchType>'
        '</CMSearchDescription>'
    )


TESTS = {
    1: ("v1: simple id+stopTime+CMR", make_v1_simple, "text/xml"),
    2: ("v2: trackID+stopTime+CMR", make_v2_trackid, "text/xml"),
    3: ("v3: id+timeSpanList+CMR", make_v3_timespan, "text/xml"),
    4: ("v4: trackID+timeSpanList+CMR", make_v4_timespan_trackid, "text/xml"),
    5: ("v5: id+timeSpanList+metadataList", make_v5_metadata, "text/xml"),
    6: ("v6: UUID+id+stopTime+CMR", make_v6_uuid_simple, "text/xml"),
    7: ("v7: id+timeSpanList+AllEvent", make_v7_allEvent_timespan, "text/xml"),
    8: ("v8: id+timeSpanList+no searchType", make_v8_no_searchtype_timespan, "text/xml"),
    9: ("v9: id+endTime+CMR", make_v9_endtime_simple, "text/xml"),
    10: ("v10: id+timeSpanList+wide+CMR", make_v10_wide_timespan, "text/xml"),
}


async def run(args):
    url = f"http://{args.ip}:{args.port}{URL_PATH}"
    test_num = args.test

    if test_num == 0:
        # Run all tests
        test_nums = list(TESTS.keys())
    else:
        test_nums = [test_num]

    print(f"\nTarget: {url}")
    print(f"Timestamps: {START_Z} → {END_Z}")
    print("=" * 70)

    for tn in test_nums:
        label, body_fn, ct = TESTS[tn]
        xml_body = body_fn()

        print(f"\n{'─' * 60}")
        print(f"  Test {tn}: {label}")
        print(f"  Content-Type: {ct}")
        print(f"  XML body:\n{xml_body[:300]}")
        print()

        try:
            async with httpx.AsyncClient(
                auth=httpx.DigestAuth(args.user, args.password),
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
                verify=False,
                follow_redirects=True,
            ) as client:
                resp = await client.post(
                    url,
                    content=xml_body.encode("utf-8"),
                    headers={
                        "Content-Type": ct,
                        "Accept": "application/xml, text/xml, */*",
                    },
                )

            sub_status = None
            status_str_val = None
            try:
                root = ET.fromstring(resp.text)
                for el in root.iter():
                    tag = el.tag.split("}")[-1]
                    if tag == "subStatusString":
                        sub_status = el.text
                    elif tag == "statusString":
                        status_str_val = el.text
            except Exception:
                pass

            status_info = f"HTTP {resp.status_code}"
            if sub_status:
                status_info += f"  ← {sub_status}"
            elif status_str_val:
                status_info += f"  ← {status_str_val}"
            else:
                status_info += "  ← (no subStatusString)"
            print(f"  RESULT: {status_info}")

            if resp.is_success:
                print(f"\n{'=' * 70}")
                print(f"  ✅ SUCCESS!")
                print(f"  Full response:\n{resp.text}")
                print(f"{'=' * 70}")
            else:
                print(f"  Full response:\n{resp.text}")

        except Exception as exc:
            print(f"  ERROR: {exc}")

        if len(test_nums) > 1:
            await asyncio.sleep(2)  # Wait between requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--port", type=int, default=80)
    parser.add_argument("--user", required=True)
    parser.add_argument("--pass", required=True, dest="password")
    parser.add_argument("--test", type=int, default=0,
                        help="Test number 1-10, or 0 for all (with 2s delay between)")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
