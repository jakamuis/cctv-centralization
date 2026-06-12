"""
discovery/uniview_client.py

Async client for Uniview NVR devices using the LAPI V1.0 protocol.

Uniview NVRs (ZNR, NVR series) expose a REST API at /LAPI/V1.0/ that uses
HTTP Digest authentication. Channel discovery is attempted via LAPI; if the
user account lacks the required permission (StatusCode 65535) we fall back to
probing RTSP streams directly.

RTSP URL pattern for Uniview NVR: rtsp://{ip}:{rtsp_port}/unicast/c{N}/s0/live
LAPI channel endpoint: GET /LAPI/V1.0/System/Resource/Channels/Video
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import List, Optional

import httpx

from app.discovery.schemas import ActiChannel

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 15.0
MAX_CHANNELS = 32
RTSP_TIMEOUT = 5.0

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*",
}


class UniviewConnectionError(Exception):
    """Device unreachable (TCP / timeout)."""


class UniviewAuthError(Exception):
    """Credentials rejected (HTTP 401 / 403 or LAPI ResponseCode 3)."""


class UniviewResponseError(Exception):
    """Unexpected response from device."""


class UniviewDeviceInfo:
    def __init__(
        self,
        device_name: Optional[str],
        model: Optional[str],
        serial_number: Optional[str],
        firmware_version: Optional[str],
        mac_address: Optional[str] = None,
    ) -> None:
        self.device_name = device_name
        self.model = model
        self.serial_number = serial_number
        self.firmware_version = firmware_version
        self.mac_address = mac_address
        self.device_type = "NVR"
        self.vendor = "uniview"


class UniviewNVRClient:
    """
    Async client for Uniview NVR LAPI + RTSP channel discovery.

    Usage
    -----
    async with UniviewNVRClient(ip, port, rtsp_port, username, password) as client:
        info = await client.get_device_info()
        channels = await client.get_channels()
    """

    def __init__(
        self,
        ip: str,
        port: int,
        rtsp_port: int,
        username: str,
        password: str,
    ) -> None:
        self._ip = ip
        self._port = port
        self._rtsp_port = rtsp_port
        self._username = username
        self._password = password
        self._base_url = f"http://{ip}:{port}"
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "UniviewNVRClient":
        self._client = httpx.AsyncClient(
            auth=httpx.DigestAuth(self._username, self._password),
            headers=_BROWSER_HEADERS,
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT,
                read=READ_TIMEOUT,
                write=5.0,
                pool=5.0,
            ),
            verify=False,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ---- public methods ----

    async def get_device_info(self) -> UniviewDeviceInfo:
        """
        Fetch device info via LAPI /LAPI/V1.0/System/DeviceInfo.
        Raises UniviewConnectionError / UniviewAuthError on failure.
        """
        url = f"{self._base_url}/LAPI/V1.0/System/DeviceInfo"
        data = await self._lapi_get(url)

        resp_data = data.get("Response", {}).get("Data", {})
        return UniviewDeviceInfo(
            device_name=resp_data.get("DeviceName"),
            model=resp_data.get("DeviceModel"),
            serial_number=resp_data.get("SerialNumber"),
            firmware_version=resp_data.get("FirmwareVersion"),
        )

    async def get_channels(self) -> List[ActiChannel]:
        """
        Discover channels. Tries LAPI first; falls back to RTSP probing.
        Returns list of found channels.
        """
        channels = await self._get_channels_via_lapi()
        if channels:
            logger.info(
                "Uniview %s:%d — %d channels via LAPI",
                self._ip, self._port, len(channels),
            )
            return channels

        logger.info(
            "Uniview %s:%d — LAPI channel list unavailable, probing RTSP streams",
            self._ip, self._port,
        )
        channels = await self._get_channels_via_rtsp()
        logger.info(
            "Uniview %s:%d — %d channels via RTSP probe",
            self._ip, self._port, len(channels),
        )
        return channels

    # ---- internal: LAPI channel discovery ----

    async def _get_channels_via_lapi(self) -> List[ActiChannel]:
        """Try to list channels via LAPI. Returns empty list on any error so RTSP fallback runs."""
        url = f"{self._base_url}/LAPI/V1.0/System/Resource/Channels/Video"
        try:
            data = await self._lapi_get(url)
            resp = data.get("Response", {})
            if resp.get("ResponseCode") != 0:
                logger.debug(
                    "Uniview LAPI channel list failed: %s (StatusCode=%s)",
                    resp.get("ResponseString"),
                    resp.get("StatusCode"),
                )
                return []

            channel_list = resp.get("Data", {}).get("VideoChannelList", [])
            channels = []
            for ch in channel_list:
                ch_id = str(ch.get("VideoChannelIndex", len(channels) + 1))
                ch_name = ch.get("ChannelName") or f"Channel {ch_id}"
                channels.append(ActiChannel(
                    channel_id=ch_id,
                    channel_name=ch_name,
                    enabled=True,
                    protocol="UNIVIEW",
                ))
            return channels

        except UniviewAuthError:
            raise  # propagate auth failure — don't silently fall through
        except Exception as exc:
            logger.debug("Uniview LAPI channel list unavailable (%s), will try RTSP", exc)
            return []

    # ---- internal: RTSP channel probing ----

    async def _get_channels_via_rtsp(self) -> List[ActiChannel]:
        """
        Probe Uniview RTSP streams: rtsp://{ip}:{rtsp_port}/unicast/c{N}/s0/live
        Stops at the first channel that is not accessible.
        """
        channels: List[ActiChannel] = []

        for n in range(1, MAX_CHANNELS + 1):
            path = f"/unicast/c{n}/s0/live"
            reachable = await self._probe_rtsp_channel(path)

            if reachable:
                channels.append(ActiChannel(
                    channel_id=str(n),
                    channel_name=f"Channel {n}",
                    enabled=True,
                    protocol="UNIVIEW",
                ))
                logger.debug("Uniview %s — RTSP channel %d found", self._ip, n)
            else:
                logger.debug("Uniview %s — RTSP channel %d not accessible, stopping", self._ip, n)
                break

        return channels

    async def _probe_rtsp_channel(self, path: str) -> bool:
        """
        Probe an RTSP channel using digest auth.

        Sends an unauthenticated DESCRIBE, parses the 401 digest challenge,
        then re-sends with credentials. Returns True only on HTTP 200.
        Channels that don't exist return 401 (no challenge accepted) or 4xx/5xx.
        """
        url = f"rtsp://{self._ip}:{self._rtsp_port}{path}"

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._ip, self._rtsp_port),
                timeout=RTSP_TIMEOUT,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            raise UniviewConnectionError(
                f"RTSP cannot connect to {self._ip}:{self._rtsp_port} — {exc}"
            ) from exc

        try:
            # Step 1: unauthenticated DESCRIBE to get digest challenge
            req1 = (
                f"DESCRIBE {url} RTSP/1.0\r\n"
                f"CSeq: 1\r\n"
                f"User-Agent: UniviewClient/1.0\r\n"
                f"\r\n"
            )
            writer.write(req1.encode())
            await asyncio.wait_for(writer.drain(), timeout=RTSP_TIMEOUT)
            resp1 = await asyncio.wait_for(reader.read(2048), timeout=RTSP_TIMEOUT)
            resp1_text = resp1.decode("utf-8", errors="replace")

            # If device responds 200 without auth (unusual), channel exists
            if "RTSP/1.0 200" in resp1_text:
                return True

            # Parse digest challenge from WWW-Authenticate header
            m = re.search(
                r'WWW-Authenticate:\s*Digest\s+realm="([^"]+)",\s*nonce="([^"]+)"',
                resp1_text, re.IGNORECASE,
            )
            if not m:
                return False  # no digest challenge → channel doesn't exist

            realm, nonce = m.group(1), m.group(2)

            # Build digest response
            ha1 = hashlib.md5(f"{self._username}:{realm}:{self._password}".encode()).hexdigest()
            ha2 = hashlib.md5(f"DESCRIBE:{url}".encode()).hexdigest()
            dig_response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            auth_header = (
                f'Digest username="{self._username}", realm="{realm}", '
                f'nonce="{nonce}", uri="{url}", response="{dig_response}"'
            )

            # Step 2: authenticated DESCRIBE
            req2 = (
                f"DESCRIBE {url} RTSP/1.0\r\n"
                f"CSeq: 2\r\n"
                f"User-Agent: UniviewClient/1.0\r\n"
                f"Authorization: {auth_header}\r\n"
                f"\r\n"
            )
            writer.write(req2.encode())
            await asyncio.wait_for(writer.drain(), timeout=RTSP_TIMEOUT)
            resp2 = await asyncio.wait_for(reader.read(512), timeout=RTSP_TIMEOUT)
            resp2_text = resp2.decode("utf-8", errors="replace")

            return "RTSP/1.0 200" in resp2_text

        except asyncio.TimeoutError:
            logger.debug("Uniview %s RTSP probe timeout for %s", self._ip, path)
            return False
        except Exception as exc:
            logger.debug("Uniview %s RTSP probe error for %s: %s", self._ip, path, exc)
            return False
        finally:
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
            except Exception:
                pass

    # ---- internal: LAPI request helper ----

    async def _lapi_get(self, url: str) -> dict:
        """
        GET a LAPI URL with digest auth. Returns parsed JSON.
        Raises UniviewConnectionError / UniviewAuthError / UniviewResponseError.
        """
        if self._client is None:
            raise RuntimeError("UniviewNVRClient must be used as async context manager")

        try:
            response = await self._client.get(url)

            if response.status_code in (401, 403):
                raise UniviewAuthError(
                    f"Authentication failed for {self._ip}:{self._port} "
                    f"(HTTP {response.status_code})"
                )
            if not response.is_success:
                raise UniviewResponseError(
                    f"HTTP {response.status_code} from {url}"
                )

            data = response.json()
            lapi_resp = data.get("Response", {})
            rc = lapi_resp.get("ResponseCode")

            if rc == 3:
                raise UniviewAuthError(
                    f"LAPI auth error (ResponseCode=3) from {self._ip}:{self._port}"
                )

            return data

        except (UniviewAuthError, UniviewResponseError):
            raise

        except httpx.TimeoutException as exc:
            raise UniviewConnectionError(
                f"Timeout connecting to {self._ip}:{self._port} — {exc}"
            ) from exc

        except httpx.ConnectError as exc:
            raise UniviewConnectionError(
                f"Cannot connect to {self._ip}:{self._port} — {exc}"
            ) from exc

        except httpx.RequestError as exc:
            raise UniviewConnectionError(
                f"Network error reaching {self._ip}:{self._port} — {exc}"
            ) from exc
