"""
Probe an ACTi NVR at the given IP to discover what API it supports.

Usage:
    python tools/probe_acti_nvr.py <ip> <username> <password> [port]

Checks:
    1. Basic HTTP reachability (port 80, 443, 8080)
    2. ACTi CGI API  — /cgi-bin/cmd/encoder?USER=...&PWD=...&GET=DevInfo
    3. ONVIF device service — /onvif/device_service (SOAP GetDeviceInformation)
    4. RTSP reachability — port 554
    5. Common ACTi RTSP stream paths
"""

import sys
import socket
import asyncio
import httpx


IP       = sys.argv[1] if len(sys.argv) > 1 else "192.168.15.200"
USER     = sys.argv[2] if len(sys.argv) > 2 else "admin"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else "123456"
PORT     = int(sys.argv[4]) if len(sys.argv) > 4 else 80


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tcp_open(ip, port, timeout=3) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ---------------------------------------------------------------------------
# ACTi CGI API probe
# ---------------------------------------------------------------------------

ACTI_CGI_PATHS = [
    "/cgi-bin/cmd/encoder",   # newer NVR7 / E-series
    "/cgi-bin/encoder",       # older ENR / NVR
    "/cgi-bin/videoin",
    "/goform/getParam",       # some ACTi models
]

ACTI_CGI_PARAMS = {
    "USER": USER,
    "PWD":  PASSWORD,
    "GET":  "DevInfo",
}

async def probe_acti_cgi(client: httpx.AsyncClient) -> bool:
    section("ACTi CGI API")
    found = False
    for path in ACTI_CGI_PATHS:
        url = f"http://{IP}:{PORT}{path}"
        try:
            r = await client.get(url, params=ACTI_CGI_PARAMS, timeout=8)
            status = r.status_code
            body_preview = r.text[:300].replace('\r\n', ' ').replace('\n', ' ')
            print(f"  {path}  →  HTTP {status}")
            if status < 400:
                print(f"    Body: {body_preview}")
                found = True
            elif status == 401:
                print(f"    Auth required — endpoint EXISTS (wrong credentials?)")
                found = True
        except httpx.ConnectError:
            print(f"  {path}  →  Connection refused")
        except httpx.TimeoutException:
            print(f"  {path}  →  Timeout")
        except Exception as e:
            print(f"  {path}  →  Error: {e}")
    return found


# ---------------------------------------------------------------------------
# ONVIF probe (SOAP GetDeviceInformation)
# ---------------------------------------------------------------------------

ONVIF_ENVELOPE = """<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <GetDeviceInformation xmlns="http://www.onvif.org/ver10/device/wsdl"/>
  </s:Body>
</s:Envelope>"""

ONVIF_PORTS = [80, 8080, 8000]
ONVIF_PATHS = ["/onvif/device_service", "/onvif/Device", "/onvif/device"]

async def probe_onvif(client: httpx.AsyncClient) -> bool:
    section("ONVIF Device Service")
    found = False
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
    for port in ONVIF_PORTS:
        for path in ONVIF_PATHS:
            url = f"http://{IP}:{port}{path}"
            try:
                r = await client.post(url, content=ONVIF_ENVELOPE, headers=headers, timeout=8)
                body_preview = r.text[:400].replace('\r\n', ' ').replace('\n', ' ')
                print(f"  {url}  →  HTTP {r.status_code}")
                if r.status_code < 500:
                    print(f"    Body: {body_preview}")
                    found = True
            except httpx.ConnectError:
                pass  # port not open — skip silently
            except httpx.TimeoutException:
                print(f"  {url}  →  Timeout")
            except Exception as e:
                print(f"  {url}  →  Error: {e}")
    return found


# ---------------------------------------------------------------------------
# HTTP root probe — check what the NVR returns at /
# ---------------------------------------------------------------------------

async def probe_http_root(client: httpx.AsyncClient):
    section(f"HTTP Root  (port {PORT})")
    url = f"http://{IP}:{PORT}/"
    try:
        r = await client.get(url, timeout=8, follow_redirects=True)
        print(f"  GET /  →  HTTP {r.status_code}")
        print(f"  Content-Type: {r.headers.get('content-type', '(none)')}")
        print(f"  Server: {r.headers.get('server', '(none)')}")
        print(f"  Body (first 500 chars):")
        print("  " + r.text[:500].replace('\n', '\n  '))
    except Exception as e:
        print(f"  Error: {e}")


# ---------------------------------------------------------------------------
# RTSP probe
# ---------------------------------------------------------------------------

RTSP_PATHS = [
    "/",
    "/live/ch00_0",           # ACTi NVR7 channel 1 main stream
    "/live/ch01_0",           # channel 2
    "/live/ch00_1",           # channel 1 sub stream
    "/stream1",               # generic
    "/Streaming/Channels/101",# Hikvision-style (some ACTi firmware)
]

def rtsp_describe(ip, port, path, user, pwd) -> str:
    uri = f"rtsp://{ip}:{port}{path}"
    request = (
        f"DESCRIBE {uri} RTSP/1.0\r\n"
        f"CSeq: 1\r\n"
        f"User-Agent: ACTi-Probe/1.0\r\n"
        f"Accept: application/sdp\r\n"
        f"Authorization: Basic {__import__('base64').b64encode(f'{user}:{pwd}'.encode()).decode()}\r\n"
        f"\r\n"
    )
    try:
        with socket.create_connection((ip, port), timeout=5) as s:
            s.sendall(request.encode())
            resp = s.recv(4096).decode(errors="replace")
            first_line = resp.split("\r\n")[0]
            return first_line
    except Exception as e:
        return f"Error: {e}"

def probe_rtsp():
    section("RTSP  (port 554)")
    if not tcp_open(IP, 554):
        print("  Port 554 is CLOSED")
        return
    print("  Port 554 is OPEN")
    for path in RTSP_PATHS:
        result = rtsp_describe(IP, 554, path, USER, PASSWORD)
        print(f"  {path:35s}  →  {result}")


# ---------------------------------------------------------------------------
# Port scan (common NVR ports)
# ---------------------------------------------------------------------------

def probe_ports():
    section("Open Ports")
    ports = {
        80:   "HTTP",
        443:  "HTTPS",
        554:  "RTSP",
        8080: "HTTP-alt / ONVIF",
        8000: "HTTP-alt",
        9090: "ACTi NVR7 HTTP",
        37777:"Dahua TCP",
    }
    for port, label in ports.items():
        status = "OPEN  ✓" if tcp_open(IP, port) else "closed"
        print(f"  {port:5d}  {label:25s}  {status}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print(f"\nACTi NVR Probe  —  target: {IP}:{PORT}  user: {USER}")

    probe_ports()
    probe_rtsp()

    async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
        await probe_http_root(client)
        await probe_acti_cgi(client)
        await probe_onvif(client)

    section("Summary")
    print("  Check above for any HTTP 200/401 responses — those indicate working endpoints.")
    print("  RTSP '200 OK' or '401 Unauthorized' = stream path exists.")
    print("  RTSP '404 Not Found' = wrong path.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
