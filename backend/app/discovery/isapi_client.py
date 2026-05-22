"""
discovery/isapi_client.py

Async Hikvision ISAPI HTTP client.

Why this file exists:
  - Encapsulates all Hikvision-specific HTTP communication in one place.
  - The sync engine calls this client; it never touches httpx directly.
  - Digest authentication is handled transparently by httpx.DigestAuth.
  - XML parsing is done with the stdlib `xml.etree.ElementTree` — no extra
    dependencies needed.

Design decisions:
  - Each public method has its own timeout so a slow channel-list call
    doesn't block the device-info call.
  - All methods return typed dataclasses / Pydantic models, never raw XML.
  - Errors are raised as specific exceptions so the sync engine can decide
    whether to mark a device as "failed" vs "unreachable".
  - Credentials are never logged — only the IP and port appear in log lines.

ISAPI endpoints used:
  GET /ISAPI/System/deviceInfo          → device name, model, serial, firmware
  GET /ISAPI/ContentMgmt/InputProxy/channels  → IP channel list (NVR only)
  GET /ISAPI/System/Video/inputs/channels     → analog channel list (fallback)
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

import httpx

from app.discovery.schemas import HikvisionDeviceInfo, HikvisionChannel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Timeout constants (seconds)
# ---------------------------------------------------------------------------

CONNECT_TIMEOUT = 10.0      # TCP handshake
READ_TIMEOUT = 20.0         # waiting for response body
CHANNEL_LIST_TIMEOUT = 30.0 # channel list can be large on big NVRs

# ---------------------------------------------------------------------------
# Hikvision XML namespace
# ---------------------------------------------------------------------------

# Most Hikvision ISAPI responses use this namespace.
# We strip it when parsing so tag lookups work without the prefix.
HIKVISION_NS = "http://www.hikvision.com/ver20/XMLSchema"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ISAPIConnectionError(Exception):
    """Raised when the device is unreachable (TCP / timeout)."""


class ISAPIAuthError(Exception):
    """Raised when credentials are rejected (HTTP 401 / 403)."""


class ISAPIResponseError(Exception):
    """Raised when the device returns an unexpected HTTP status or body."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class HikvisionISAPIClient:
    """
    Async client for the Hikvision ISAPI REST interface.

    Usage
    -----
    async with HikvisionISAPIClient(ip, port, username, password) as client:
        info = await client.get_device_info()
        channels = await client.get_ip_channels()
    """

    def __init__(
        self,
        ip: str,
        port: int,
        username: str,
        password: str,
        use_https: bool = False,
    ) -> None:
        self._ip = ip
        self._port = port
        self._username = username
        self._password = password
        scheme = "https" if use_https else "http"
        self._base_url = f"{scheme}://{ip}:{port}"
        self._client: Optional[httpx.AsyncClient] = None

    # ---- context manager ----

    async def __aenter__(self) -> "HikvisionISAPIClient":
        self._client = httpx.AsyncClient(
            auth=httpx.DigestAuth(self._username, self._password),
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT,
                read=READ_TIMEOUT,
                write=10.0,
                pool=5.0,
            ),
            verify=False,           # NVRs often use self-signed certs
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ---- public methods ----

    async def get_device_info(self) -> HikvisionDeviceInfo:
        """
        Fetch /ISAPI/System/deviceInfo and return a HikvisionDeviceInfo.

        This is also used as the connectivity probe — if this call succeeds
        the device is reachable and credentials are valid.
        """

        url = f"{self._base_url}/ISAPI/System/deviceInfo"
        logger.debug("ISAPI deviceInfo → %s:%d", self._ip, self._port)

        xml_text = await self._get(url)
        return _parse_device_info(xml_text)

    async def get_ip_channels(self) -> List[HikvisionChannel]:
        """
        Fetch /ISAPI/ContentMgmt/InputProxy/channels (IP channels on NVR).

        Returns an empty list if the endpoint is not supported by the device
        (e.g. standalone cameras, older firmware).
        """

        url = f"{self._base_url}/ISAPI/ContentMgmt/InputProxy/channels"
        logger.debug("ISAPI InputProxy/channels → %s:%d", self._ip, self._port)

        try:
            xml_text = await self._get(url, timeout_override=CHANNEL_LIST_TIMEOUT)
            return _parse_ip_channels(xml_text)
        except ISAPIResponseError as exc:
            # 404 / 400 means the device doesn't support this endpoint
            logger.info(
                "%s:%d — InputProxy/channels not supported (%s), returning []",
                self._ip, self._port, exc,
            )
            return []

    async def get_analog_channels(self) -> List[HikvisionChannel]:
        """
        Fetch /ISAPI/System/Video/inputs/channels (analog / encoder channels).

        Used as a fallback when the device is a DVR or encoder rather than
        an IP NVR.
        """

        url = f"{self._base_url}/ISAPI/System/Video/inputs/channels"
        logger.debug("ISAPI Video/inputs/channels → %s:%d", self._ip, self._port)

        try:
            xml_text = await self._get(url, timeout_override=CHANNEL_LIST_TIMEOUT)
            return _parse_analog_channels(xml_text)
        except ISAPIResponseError as exc:
            logger.info(
                "%s:%d — Video/inputs/channels not supported (%s), returning []",
                self._ip, self._port, exc,
            )
            return []

    # ---- internal HTTP helper ----

    async def _get(
        self,
        url: str,
        timeout_override: Optional[float] = None,
    ) -> str:
        """
        Perform a GET request and return the response body as a string.

        Raises
        ------
        ISAPIConnectionError  — TCP / timeout failure
        ISAPIAuthError        — HTTP 401 or 403
        ISAPIResponseError    — any other non-2xx status
        """

        if self._client is None:
            raise RuntimeError(
                "HikvisionISAPIClient must be used as an async context manager"
            )

        try:
            kwargs = {}
            if timeout_override is not None:
                kwargs["timeout"] = httpx.Timeout(
                    connect=CONNECT_TIMEOUT,
                    read=timeout_override,
                    write=10.0,
                    pool=5.0,
                )

            response = await self._client.get(url, **kwargs)

        except httpx.TimeoutException as exc:
            raise ISAPIConnectionError(
                f"Timeout connecting to {self._ip}:{self._port} — {exc}"
            ) from exc

        except httpx.ConnectError as exc:
            raise ISAPIConnectionError(
                f"Cannot connect to {self._ip}:{self._port} — {exc}"
            ) from exc

        except httpx.RequestError as exc:
            raise ISAPIConnectionError(
                f"Network error reaching {self._ip}:{self._port} — {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise ISAPIAuthError(
                f"Authentication failed for {self._ip}:{self._port} "
                f"(HTTP {response.status_code})"
            )

        if not response.is_success:
            raise ISAPIResponseError(
                f"HTTP {response.status_code} from {url}"
            )

        return response.text


# ---------------------------------------------------------------------------
# XML parsers
# ---------------------------------------------------------------------------

def _strip_ns(tag: str) -> str:
    """Remove the Hikvision XML namespace prefix from a tag name."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _find_text(element: ET.Element, tag: str) -> Optional[str]:
    """
    Find a child element by tag (ignoring namespace) and return its text.
    Returns None if not found or text is empty.
    """
    for child in element.iter():
        if _strip_ns(child.tag) == tag:
            text = (child.text or "").strip()
            return text if text else None
    return None


def _parse_device_info(xml_text: str) -> HikvisionDeviceInfo:
    """
    Parse the /ISAPI/System/deviceInfo XML response.

    Example snippet:
      <DeviceInfo>
        <deviceName>DS-7616NI-K2</deviceName>
        <deviceID>...</deviceID>
        <model>DS-7616NI-K2</model>
        <serialNumber>DS-7616NI-K2...</serialNumber>
        <macAddress>xx:xx:xx:xx:xx:xx</macAddress>
        <firmwareVersion>V4.30.085</firmwareVersion>
        <encoderVersion>V7.3</encoderVersion>
        <deviceType>NVR</deviceType>
      </DeviceInfo>
    """

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ISAPIResponseError(f"Invalid XML in deviceInfo response: {exc}") from exc

    return HikvisionDeviceInfo(
        device_name=_find_text(root, "deviceName"),
        device_id=_find_text(root, "deviceID"),
        model=_find_text(root, "model"),
        serial_number=_find_text(root, "serialNumber"),
        mac_address=_find_text(root, "macAddress"),
        firmware_version=_find_text(root, "firmwareVersion"),
        encoder_version=_find_text(root, "encoderVersion"),
        device_type=_find_text(root, "deviceType"),
    )


def _parse_ip_channels(xml_text: str) -> List[HikvisionChannel]:
    """
    Parse /ISAPI/ContentMgmt/InputProxy/channels XML.

    Example snippet:
      <InputProxyChannelList>
        <InputProxyChannel>
          <id>1</id>
          <name>Camera 01</name>
          <sourceInputPortDescriptor>
            <ipAddress>192.168.1.64</ipAddress>
            <managePort>8000</managePort>
            <srcInputPort>1</srcInputPort>
            <streamType>auto</streamType>
            <deviceID>...</deviceID>
            <type>HIKVISION</type>
          </sourceInputPortDescriptor>
          <enable>true</enable>
        </InputProxyChannel>
        ...
      </InputProxyChannelList>
    """

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ISAPIResponseError(
            f"Invalid XML in InputProxy/channels response: {exc}"
        ) from exc

    channels: List[HikvisionChannel] = []

    for ch_elem in root.iter():
        if _strip_ns(ch_elem.tag) != "InputProxyChannel":
            continue

        channel_id = _find_text(ch_elem, "id") or ""
        channel_name = _find_text(ch_elem, "name")
        enabled_str = (_find_text(ch_elem, "enable") or "true").lower()
        enabled = enabled_str in ("true", "1", "yes")

        # IP address and port live inside sourceInputPortDescriptor
        ip_address = _find_text(ch_elem, "ipAddress")
        manage_port_str = _find_text(ch_elem, "managePort")
        protocol = _find_text(ch_elem, "type")

        manage_port: Optional[int] = None
        if manage_port_str:
            try:
                manage_port = int(manage_port_str)
            except ValueError:
                pass

        channels.append(
            HikvisionChannel(
                channel_id=channel_id,
                channel_name=channel_name,
                ip_address=ip_address,
                manage_port=manage_port,
                protocol=protocol,
                enabled=enabled,
            )
        )

    logger.debug("Parsed %d IP channels from InputProxy/channels", len(channels))
    return channels


def _parse_analog_channels(xml_text: str) -> List[HikvisionChannel]:
    """
    Parse /ISAPI/System/Video/inputs/channels XML (analog / DVR channels).

    Example snippet:
      <VideoInputChannelList>
        <VideoInputChannel>
          <id>1</id>
          <inputPort>1</inputPort>
          <name>Camera 01</name>
          <videoFormat>PAL</videoFormat>
        </VideoInputChannel>
        ...
      </VideoInputChannelList>
    """

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ISAPIResponseError(
            f"Invalid XML in Video/inputs/channels response: {exc}"
        ) from exc

    channels: List[HikvisionChannel] = []

    for ch_elem in root.iter():
        if _strip_ns(ch_elem.tag) != "VideoInputChannel":
            continue

        channel_id = _find_text(ch_elem, "id") or _find_text(ch_elem, "inputPort") or ""
        channel_name = _find_text(ch_elem, "name")

        channels.append(
            HikvisionChannel(
                channel_id=channel_id,
                channel_name=channel_name,
                ip_address=None,        # analog channels have no IP
                manage_port=None,
                protocol="ANALOG",
                enabled=True,
            )
        )

    logger.debug("Parsed %d analog channels from Video/inputs/channels", len(channels))
    return channels
