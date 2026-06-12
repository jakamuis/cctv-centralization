"""
discovery/acti_client.py

Async HTTP client for ACTi "Connect Vision" SNVR devices.

Why this file exists:
  - ACTi SNVRs have no ISAPI, ONVIF, or documented REST API.
  - The only accessible interface is HTTP Basic auth over port 80.
  - Live video is served as multipart/x-mixed-replace with H.264 chunks at
    /virtualcamera/channelN?media&streamid=0
  - Channel discovery is done by probing each channel URL until a non-200
    response is received.
  - Device info is synthesised (no machine-readable info endpoint).

Probed endpoints:
  GET /virtualcamera/channel{N}?media&streamid=0
      → HTTP 200  = channel exists and is accessible
      → HTTP 4xx  = channel does not exist (stop probing)
      → timeout   = NVR unreachable

Max channels probed: 32 (typical SNVR limit).
"""

from __future__ import annotations

import logging
from typing import List, Optional

import httpx

from app.discovery.schemas import ActiDeviceInfo, ActiChannel

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 8.0
MAX_CHANNELS = 32

# ACTi SNVRs sometimes drop connections for non-browser User-Agents
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


# ---------------------------------------------------------------------------
# Custom exceptions (parallel to isapi_client.py)
# ---------------------------------------------------------------------------

class ActiConnectionError(Exception):
    """Raised when the device is unreachable (TCP / timeout)."""


class ActiAuthError(Exception):
    """Raised when credentials are rejected (HTTP 401 / 403)."""


class ActiResponseError(Exception):
    """Raised when the device returns an unexpected HTTP status."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class ActiSNVRClient:
    """
    Async client for ACTi SNVR HTTP streaming interface.

    Usage
    -----
    async with ActiSNVRClient(ip, port, username, password) as client:
        info = await client.get_device_info()
        channels = await client.get_channels()
    """

    def __init__(
        self,
        ip: str,
        port: int,
        username: str,
        password: str,
    ) -> None:
        self._ip = ip
        self._port = port
        self._username = username
        self._password = password
        self._base_url = f"http://{ip}:{port}"
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ActiSNVRClient":
        self._client = httpx.AsyncClient(
            auth=httpx.BasicAuth(self._username, self._password),
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

    async def get_device_info(self) -> ActiDeviceInfo:
        """
        Probe connectivity and return synthesised device info.

        ACTi SNVRs have no machine-readable info endpoint. We probe the root
        URL first (lighter, always responds in browser), then fall back to the
        channel 1 stream URL. Raises ActiConnectionError / ActiAuthError on
        failure.
        """
        logger.debug("ACTi probe connectivity → %s:%d", self._ip, self._port)

        # Prefer the root page — it responds to any HTTP client and confirms
        # the server is up without needing to negotiate a video stream.
        root_url = f"{self._base_url}/"
        channel_url = f"{self._base_url}/virtualcamera/channel1?media&streamid=0"

        try:
            await self._head_or_get(root_url)
        except ActiResponseError:
            # Some root pages return non-2xx but the server IS alive; that's fine.
            pass
        except ActiConnectionError:
            # Root failed — try the channel endpoint before giving up.
            logger.debug(
                "ACTi root probe failed, trying channel1 endpoint for %s:%d",
                self._ip, self._port,
            )
            await self._head_or_get(channel_url)

        return ActiDeviceInfo(
            device_name=f"ACTi SNVR @ {self._ip}",
            device_type="NVR",
            vendor="acti_snvr",
        )

    async def get_channels(self) -> List[ActiChannel]:
        """
        Discover channels by probing /virtualcamera/channelN?media&streamid=0
        for N = 1 … MAX_CHANNELS.

        Stops at the first channel that returns a non-200 status.
        Returns the list of channels that responded with HTTP 200.
        """
        channels: List[ActiChannel] = []

        for n in range(1, MAX_CHANNELS + 1):
            url = f"{self._base_url}/virtualcamera/channel{n}?media&streamid=0"
            try:
                status = await self._probe_channel(url)
            except ActiConnectionError:
                logger.warning(
                    "ACTi %s:%d — connection lost probing channel %d, stopping",
                    self._ip, self._port, n,
                )
                break

            if status == 200:
                channels.append(
                    ActiChannel(
                        channel_id=str(n),
                        channel_name=f"Channel {n}",
                        enabled=True,
                    )
                )
                logger.debug("ACTi %s:%d — channel %d found", self._ip, self._port, n)
            else:
                logger.debug(
                    "ACTi %s:%d — channel %d returned HTTP %d, stopping probe",
                    self._ip, self._port, n, status,
                )
                break

        logger.info(
            "ACTi %s:%d — discovered %d channels",
            self._ip, self._port, len(channels),
        )
        return channels

    # ---- internal helpers ----

    async def _head_or_get(self, url: str) -> None:
        """
        Perform a GET request (reading only the headers, not the body).
        Raises ActiConnectionError / ActiAuthError / ActiResponseError.
        """
        if self._client is None:
            raise RuntimeError("ActiSNVRClient must be used as async context manager")

        try:
            # Stream so we get headers without reading the video body
            async with self._client.stream("GET", url) as r:
                if r.status_code in (401, 403):
                    raise ActiAuthError(
                        f"Authentication failed for {self._ip}:{self._port} "
                        f"(HTTP {r.status_code})"
                    )
                if not r.is_success:
                    raise ActiResponseError(
                        f"HTTP {r.status_code} from {url}"
                    )

        except (ActiAuthError, ActiResponseError):
            raise

        except httpx.TimeoutException as exc:
            raise ActiConnectionError(
                f"Timeout connecting to {self._ip}:{self._port} — {exc}"
            ) from exc

        except httpx.ConnectError as exc:
            raise ActiConnectionError(
                f"Cannot connect to {self._ip}:{self._port} — {exc}"
            ) from exc

        except httpx.RequestError as exc:
            raise ActiConnectionError(
                f"Network error reaching {self._ip}:{self._port} — {exc}"
            ) from exc

    async def _probe_channel(self, url: str) -> int:
        """
        Probe a channel URL and return its HTTP status code.
        Returns -1 on connection failure (raises ActiConnectionError).
        """
        if self._client is None:
            raise RuntimeError("ActiSNVRClient must be used as async context manager")

        try:
            async with self._client.stream("GET", url) as r:
                return r.status_code

        except httpx.TimeoutException as exc:
            raise ActiConnectionError(
                f"Timeout probing {url} — {exc}"
            ) from exc

        except httpx.ConnectError as exc:
            raise ActiConnectionError(
                f"Cannot connect while probing {url} — {exc}"
            ) from exc

        except httpx.RequestError as exc:
            raise ActiConnectionError(
                f"Network error probing {url} — {exc}"
            ) from exc
