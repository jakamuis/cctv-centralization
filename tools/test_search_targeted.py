"""
Round 5 - CamelCase XML + full track list.

Key findings:
- HDD: freeSpace=0 (drives full of recordings)
- Track 101: Enable=false, Duration=P0DT0H (disabled/empty)
- NVR uses CamelCase in its OWN XML - try CamelCase in search request
"""
import asyncio, sys, httpx

NVR = "192.168.2.100"; PORT = 80
USER = sys.argv[1]; PASS = sys.argv[2]
URL  = f"http://{NVR}:{PORT}/ISAPI/ContentMgmt/search"

START = "2026-05-22T09:17:13Z"; END = "2026-05-22T10:30:50Z"
HIK = "http://www.hikvision.com/ver20/XMLSchema"

POSTS = [
    # ---- CamelCase elements ----
    ("C1: CamelCase - StartTime/EndTime inside TimeSpanList",
     f'<?xml version="1.0" encoding="UTF-8"?>'
     f'<CMSearchDescription>'
     f'<SearchID>1</SearchID>'
     f'<TrackList><ID>101</ID></TrackList>'
     f'<TimeSpanList><TimeSpan>'
     f'<StartTime>{START}</StartTime>'
     f'<EndTime>{END}</EndTime>'
     f'</TimeSpan></TimeSpanList>'
     f'<MaxResults>40</MaxResults>'
     f'<SearchResultPostion>0</SearchResultPostion>'
     f'<SearchType>CMR</SearchType>'
     f'</CMSearchDescription>'),

    ("C2: CamelCase - flat StartTime/EndTime",
     f'<?xml version="1.0" encoding="UTF-8"?>'
     f'<CMSearchDescription>'
     f'<SearchID>1</SearchID>'
     f'<TrackList><ID>101</ID></TrackList>'
     f'<StartTime>{START}</StartTime>'
     f'<EndTime>{END}</EndTime>'
     f'<MaxResults>40</MaxResults>'
     f'<SearchResultPostion>0</SearchResultPostion>'
     f'<SearchType>CMR</SearchType>'
     f'</CMSearchDescription>'),

    # ---- Try with ENABLED track (need to find one first) ----
    # Track 201 = Channel 2 (IPCamera 02)
    ("E1: standard, track 201 (channel 2)",
     f'<?xml version="1.0" encoding="UTF-8"?>'
     f'<CMSearchDescription>'
     f'<searchID>1</searchID>'
     f'<trackList><id>201</id></trackList>'
     f'<timeSpanList><timeSpan>'
     f'<startTime>{START}</startTime>'
     f'<endTime>{END}</endTime>'
     f'</timeSpan></timeSpanList>'
     f'<maxResults>40</maxResults>'
     f'<searchResultPostion>0</searchResultPostion>'
     f'</CMSearchDescription>'),

    # ---- Try with Hikvision xmlns on root + CamelCase ----
    ("C3: Hik NS + CamelCase + TrackID + TimeSpanList",
     f'<?xml version="1.0" encoding="UTF-8"?>'
     f'<CMSearchDescription xmlns="{HIK}">'
     f'<SearchID>1</SearchID>'
     f'<TrackList><TrackID>101</TrackID></TrackList>'
     f'<TimeSpanList><TimeSpan>'
     f'<StartTime>{START}</StartTime>'
     f'<EndTime>{END}</EndTime>'
     f'</TimeSpan></TimeSpanList>'
     f'<MaxResults>40</MaxResults>'
     f'<SearchResultPostion>0</SearchResultPostion>'
     f'</CMSearchDescription>'),

    # ---- duration instead of endTime ----
    ("D1: startTime + duration (ISO 8601) instead of endTime",
     f'<?xml version="1.0" encoding="UTF-8"?>'
     f'<CMSearchDescription>'
     f'<searchID>1</searchID>'
     f'<trackList><id>101</id></trackList>'
     f'<timeSpanList><timeSpan>'
     f'<startTime>{START}</startTime>'
     f'<duration>PT4800S</duration>'
     f'</timeSpan></timeSpanList>'
     f'<maxResults>40</maxResults>'
     f'<searchResultPostion>0</searchResultPostion>'
     f'</CMSearchDescription>'),
]

GETS = [
    # Get all tracks
    ("All tracks",     f"http://{NVR}:{PORT}/ISAPI/ContentMgmt/record/tracks"),
    # Check track 201 specifically
    ("Track 201",      f"http://{NVR}:{PORT}/ISAPI/ContentMgmt/record/tracks/201"),
    ("Track 301",      f"http://{NVR}:{PORT}/ISAPI/ContentMgmt/record/tracks/301"),
    ("Track 401",      f"http://{NVR}:{PORT}/ISAPI/ContentMgmt/record/tracks/401"),
]

async def main():
    async with httpx.AsyncClient(
        auth=httpx.DigestAuth(USER, PASS),
        timeout=httpx.Timeout(connect=10, read=30, write=10, pool=5),
        verify=False, follow_redirects=True,
    ) as c:
        print("=== GET FULL TRACK LIST ===")
        r = await c.get(f"http://{NVR}:{PORT}/ISAPI/ContentMgmt/record/tracks",
                        headers={"Accept": "application/xml"})
        # Print full response to see ALL tracks
        print(f"HTTP {r.status_code}")
        print(r.text[:5000])
        await asyncio.sleep(1)

        print("\n=== SEARCH TESTS ===")
        for label, body in POSTS:
            print(f"\n{'='*60}\n{label}")
            r = await c.post(URL, content=body.encode(),
                headers={"Content-Type":"application/xml","Accept":"application/xml,*/*"})
            print(f"HTTP {r.status_code}\n{r.text[:500]}")
            if r.is_success:
                print("*** SUCCESS ***"); break
            await asyncio.sleep(3)

asyncio.run(main())
