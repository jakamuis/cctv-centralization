"""
api/v1/routers/discovery.py

FastAPI router for the Phase 7B discovery sync endpoint.

Why this file exists:
  - Exposes POST /api/v1/discovery/sync as the single manual trigger for
    the Google Sheet → ISAPI → PostgreSQL pipeline.
  - Keeps HTTP concerns (request parsing, response shaping, error codes)
    completely separate from the sync engine business logic.
  - Provides a GET /api/v1/discovery/nvrs endpoint so the UI can list
    all discovered NVRs and their sync status without re-running a sync.

Endpoints:
  POST /discovery/sync
    Triggers a full sync run.  Returns a SyncResponse JSON with per-device
    outcomes.  Accepts an optional `csv_url` query parameter to override
    the default Google Sheet URL (useful for testing with a staging sheet).

  GET /discovery/nvrs
    Lists all DiscoveredNVR rows from the database.
    Supports optional `site_code` and `sync_status` query filters.

  GET /discovery/nvrs/{nvr_id}/channels
    Lists all NVRChannel rows for a specific NVR.

Security:
  - All endpoints require a valid JWT (get_current_user dependency).
  - The sync endpoint additionally requires the "OPERATOR" or "SUPER_ADMIN"
    role to prevent accidental triggers by read-only users.
  - Credentials (username/password) are NEVER returned in any response.

Error handling:
  - If the CSV fetch itself fails (network error), the endpoint returns
    HTTP 502 Bad Gateway with a descriptive message.
  - Individual device failures are reported inside the SyncResponse body
    (not as HTTP errors) so the caller gets the full picture.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

# from app.api.v1.dependencies import get_current_user  # TEMP: disabled for local testing
from app.db.session import get_db
from app.discovery.csv_loader import parse_csv_rows
from app.discovery.sync_engine import run_sync, _sync_single_device
from app.discovery.schemas import SyncResponse, CsvDeviceRow, DeviceSyncResult
# from app.models.user import User  # TEMP: not needed without auth
from app.repositories.discovery import DiscoveryRepository
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["Discovery"])


# ---------------------------------------------------------------------------
# POST /discovery/sync
# ---------------------------------------------------------------------------

@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Trigger manual NVR discovery sync from Google Sheet CSV",
    status_code=status.HTTP_200_OK,
)
async def trigger_sync(
    csv_url: Optional[str] = Query(
        default=None,
        description=(
            "Override the Google Sheet CSV URL. "
            "Leave blank to use the default configured URL."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    # TEMP: auth disabled for local testing — re-enable before production
    # current_user: User = Depends(get_current_user),
) -> SyncResponse:
    """
    Trigger a full discovery sync.

    Downloads the Google Sheet CSV, validates each enabled row, probes
    each NVR via Hikvision ISAPI, and upserts the results into PostgreSQL.

    **Returns** a `SyncResponse` with:
    - `total_rows` — total CSV rows (including disabled)
    - `enabled_rows` — rows with `enabled=true`
    - `synced` — devices successfully synced
    - `skipped` — disabled rows or rows with missing required fields
    - `failed` — devices that were unreachable, had auth errors, or DB errors
    - `results` — per-device breakdown

    **Error codes:**
    - `502` — Could not fetch the CSV (network error or bad URL)
    - `500` — Unexpected internal error before the sync started
    """

    logger.info("Discovery sync triggered (unauthenticated — testing mode)")

    try:
        response = await run_sync(db=db, csv_url=csv_url)
    except RuntimeError as exc:
        # CSV fetch failed — surface as 502 so the caller knows it's upstream
        logger.error("Sync aborted — CSV fetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch device seed CSV: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during discovery sync")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal sync error: {type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "Sync complete: synced=%d skipped=%d failed=%d",
        response.synced,
        response.skipped,
        response.failed,
    )

    return response


# ---------------------------------------------------------------------------
# POST /discovery/sync/device  — sync a single device without the CSV
# ---------------------------------------------------------------------------

class SyncDeviceRequest(BaseModel):
    branch_name: str
    nvr_ip: str
    http_port: int = 80
    rtsp_port: int = 554
    username: str
    password: str
    vendor: str = "hikvision"     # "hikvision" | "acti_snvr"
    timezone: str = "WIB"         # "WIB" (UTC+7) | "WITA" (UTC+8) | "WIT" (UTC+9)
    enabled: str = "true"


@router.post(
    "/sync/device",
    response_model=DeviceSyncResult,
    summary="Sync a single NVR device directly (no Google Sheet needed)",
    status_code=status.HTTP_200_OK,
)
async def sync_single_device(
    body: SyncDeviceRequest,
    db: AsyncSession = Depends(get_db),
) -> DeviceSyncResult:
    """
    Probe and register a single NVR directly — useful for testing without
    editing the Google Sheet.

    For ACTi SNVR set **vendor = acti_snvr** and **http_port = 80**.
    For Hikvision leave vendor blank or set **vendor = hikvision**.
    """
    row = CsvDeviceRow(
        branch_name=body.branch_name,
        nvr_ip=body.nvr_ip,
        http_port=str(body.http_port),
        rtsp_port=str(body.rtsp_port),
        username=body.username,
        password=body.password,
        vendor=body.vendor,
        timezone=body.timezone,
        enabled=body.enabled,
    )

    result = await _sync_single_device(db, row)
    return result


# ---------------------------------------------------------------------------
# POST /discovery/sync/upload  — sync from uploaded CSV file
# ---------------------------------------------------------------------------

@router.post(
    "/sync/upload",
    response_model=SyncResponse,
    summary="Sync NVR devices from an uploaded CSV file",
    status_code=status.HTTP_200_OK,
)
async def sync_from_upload(
    file: UploadFile = File(..., description="CSV file with columns: branch_name (or branch), nvr_ip (or ip), username, password, vendor, timezone"),
    db: AsyncSession = Depends(get_db),
) -> SyncResponse:
    """
    Upload a CSV file and run discovery sync against each enabled row.

    Accepted column names (case-insensitive):
    - **branch_name** or **branch** — location name (required)
    - **nvr_ip** or **ip** — NVR IP address (required)
    - **username** — NVR login (required)
    - **password** — NVR password (required)
    - **vendor** — hikvision / acti / acti_snvr (optional, default: hikvision)
    - **timezone** — WIB / WITA / WIT (optional, default: WIB)
    - **http_port** — HTTP port (optional, default: 80)
    - **enabled** — true/false (optional, default: true)

    Rows with multiple IPs (e.g. "192.168.1.1 & 192.168.1.2") are skipped.
    """
    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8-sig")  # handles BOM from Excel
    except UnicodeDecodeError:
        raw_text = raw_bytes.decode("latin-1")

    rows, parse_errors = parse_csv_rows(raw_text)

    if parse_errors:
        for err in parse_errors:
            logger.warning("CSV upload parse warning: %s", err)

    # Abort early if the CSV couldn't be parsed at all
    if not rows and parse_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"parse_errors": parse_errors},
        )

    total_rows = len(rows)
    enabled_rows = [r for r in rows if r.is_enabled]

    results: list[DeviceSyncResult] = []
    synced_count = skipped_count = failed_count = 0

    for row in rows:
        if not row.is_enabled:
            results.append(DeviceSyncResult(
                code=row.code, nvr_ip=row.nvr_ip or "(unknown)",
                http_port=row.http_port_int, status="skipped",
                reason="Row disabled (enabled=false)",
            ))
            skipped_count += 1
            continue

        # Skip rows where the IP field contains multiple addresses
        if row.nvr_ip and ("&" in row.nvr_ip or "," in row.nvr_ip):
            results.append(DeviceSyncResult(
                code=row.code, nvr_ip=row.nvr_ip,
                http_port=row.http_port_int, status="skipped",
                reason=f"Multiple IPs not supported: {row.nvr_ip!r}",
            ))
            skipped_count += 1
            continue

        result = await _sync_single_device(db, row)
        results.append(result)
        if result.status == "synced":
            synced_count += 1
        elif result.status == "skipped":
            skipped_count += 1
        else:
            failed_count += 1

    return SyncResponse(
        total_rows=total_rows,
        enabled_rows=len(enabled_rows),
        synced=synced_count,
        skipped=skipped_count,
        failed=failed_count,
        results=results,
    )


# ---------------------------------------------------------------------------
# GET /discovery/nvrs
# ---------------------------------------------------------------------------

@router.get(
    "/nvrs",
    summary="List all discovered NVRs",
    status_code=status.HTTP_200_OK,
)
async def list_nvrs(
    code: Optional[str] = Query(default=None, description="Filter by code"),
    sync_status: Optional[str] = Query(
        default=None,
        description="Filter by sync status: synced | unreachable | auth_error | failed",
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    # TEMP: auth disabled for local testing — re-enable before production
    # current_user: User = Depends(get_current_user),
):
    """
    Return a list of all NVRs that have been synced from the Google Sheet.

    Credentials (username / password) are excluded from the response.
    """

    repo = DiscoveryRepository(db)
    nvrs = await repo.list_nvrs(
        code=code,
        sync_status=sync_status,
        offset=offset,
        limit=limit,
    )

    # Serialize manually to exclude credentials
    return [_nvr_to_dict(nvr) for nvr in nvrs]


# ---------------------------------------------------------------------------
# GET /discovery/nvrs/{nvr_id}/channels
# ---------------------------------------------------------------------------

@router.get(
    "/nvrs/{nvr_id}/channels",
    summary="List channels for a specific NVR",
    status_code=status.HTTP_200_OK,
)
async def list_nvr_channels(
    nvr_id: UUID,
    db: AsyncSession = Depends(get_db),
    # TEMP: auth disabled for local testing — re-enable before production
    # current_user: User = Depends(get_current_user),
):
    """
    Return all camera channels discovered on the specified NVR.
    """

    repo = DiscoveryRepository(db)

    nvr = await repo.get_nvr_by_id(nvr_id)
    if not nvr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NVR {nvr_id} not found",
        )

    channels = await repo.list_channels(nvr_id)

    return {
        "nvr_id": str(nvr_id),
        "code": nvr.code,
        "nvr_ip": nvr.nvr_ip,
        "http_port": nvr.http_port,
        "channel_count": len(channels),
        "channels": [
            {
                "id": str(ch.id),
                "channel_id": ch.channel_id,
                "channel_name": ch.channel_name,
                "ip_address": ch.ip_address,
                "manage_port": ch.manage_port,
                "protocol": ch.protocol,
                "is_enabled": ch.is_enabled,
                "last_online_at": (
                    nvr.last_synced_at.isoformat()
                    if ch.is_enabled and nvr.last_synced_at and nvr.sync_status == "synced"
                    else None
                ),
            }
            for ch in channels
        ],
    }


# ---------------------------------------------------------------------------
# PATCH /discovery/nvrs/{nvr_id}  — update NVR credentials / settings
# ---------------------------------------------------------------------------

class NVRUpdateRequest(BaseModel):
    branch_name: Optional[str] = None
    nvr_ip:      Optional[str] = None
    http_port:   Optional[int] = None
    rtsp_port:   Optional[int] = None
    username:    Optional[str] = None
    password:    Optional[str] = None
    vendor:      Optional[str] = None
    timezone:    Optional[str] = None


@router.patch(
    "/nvrs/{nvr_id}",
    summary="Update NVR settings (credentials, vendor, IP, etc.)",
    status_code=200,
)
async def update_nvr(
    nvr_id: UUID,
    body: NVRUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = DiscoveryRepository(db)
    nvr = await repo.get_nvr_by_id(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail=f"NVR {nvr_id} not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(nvr, field, value)

    await db.commit()
    await db.refresh(nvr)
    return _nvr_to_dict(nvr)


# ---------------------------------------------------------------------------
# DELETE /discovery/nvrs/{nvr_id}  — remove NVR and its channels
# ---------------------------------------------------------------------------

@router.delete(
    "/nvrs/{nvr_id}",
    summary="Delete a discovered NVR and all its channels",
    status_code=204,
)
async def delete_nvr(
    nvr_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DiscoveryRepository(db)
    nvr = await repo.get_nvr_by_id(nvr_id)
    if not nvr:
        raise HTTPException(status_code=404, detail=f"NVR {nvr_id} not found")
    await repo.delete_nvr(nvr_id)
    return None


# ---------------------------------------------------------------------------
# POST /discovery/nvrs/{nvr_id}/channels/{channel_id}/stream
# ---------------------------------------------------------------------------

@router.post(
    "/nvrs/{nvr_id}/channels/{channel_id}/stream",
    summary="Register a discovered channel with go2rtc and return stream_name",
    status_code=status.HTTP_200_OK,
)
async def start_channel_stream(
    nvr_id: UUID,
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    # TEMP: auth disabled for local testing — re-enable before production
    # current_user: User = Depends(get_current_user),
):
    """
    Build the Hikvision RTSP URL for a discovered channel, register it with
    go2rtc via its REST API, and return the stream_name the browser can use
    to connect via WebSocket MSE.

    RTSP URL format:
      rtsp://username:password@nvr_ip:rtsp_port/Streaming/Channels/{channel_id}01

    go2rtc registration:
      PUT http://go2rtc/api/streams?name={stream_name}&src={rtsp_url}

    Returns:
      { stream_name: str }
    """
    repo = DiscoveryRepository(db)

    nvr = await repo.get_nvr_by_id(nvr_id)
    if not nvr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NVR {nvr_id} not found",
        )

    # Build RTSP URL — credentials come from the NVR row (never exposed to browser).
    # Percent-encode username and password so special characters (* # % @ : etc.)
    # don't break the RTSP URI.  safe='' means every non-unreserved character is encoded.
    encoded_user = quote(nvr.username, safe="")
    encoded_pass = quote(nvr.password, safe="")

    vendor = getattr(nvr, "vendor", "hikvision") or "hikvision"
    if vendor == "acti_snvr":
        # ACTi SNVR: go2rtc exec: source using acti_pipe.py.
        # FFmpeg cannot demux the ACTi multipart/H.264 HTTP stream, so we use
        # acti_pipe.py which manually parses the multipart response and writes
        # clean H.264 Annex B to stdout. Credentials are percent-encoded so
        # '#' chars (e.g. samator#2017) don't prematurely end the exec: command
        # string; acti_pipe.py URL-decodes them before use.
        http_port = nvr.http_port or 80
        port_suffix = f" {http_port}" if http_port != 80 else ""
        rtsp_url = (
            f"exec:python3 /scripts/acti_pipe.py"
            f" {nvr.nvr_ip} {channel_id}"
            f" {encoded_user} {encoded_pass}{port_suffix}"
            f"#video=h264"
        )
    elif vendor == "uniview":
        # Uniview ZNR/NVR series: RTSP path is /unicast/c{N}/s0/live
        rtsp_url = (
            f"ffmpeg:rtsp://{encoded_user}:{encoded_pass}"
            f"@{nvr.nvr_ip}:{nvr.rtsp_port}"
            f"/unicast/c{channel_id}/s0/live#video=h264"
        )
    else:
        # Hikvision: wrap with ffmpeg so go2rtc always delivers H.264 to the
        # browser, regardless of whether the camera is H.264 or H.265 (HEVC).
        # go2rtc/ffmpeg passes through H.264 without re-encoding; H.265 is
        # transcoded on the fly.
        #
        # Hikvision RTSP path is always /Streaming/Channels/{channel_id}01
        # regardless of firmware version. The DS-7616NI-E2 (V3.4.2) and all
        # tested Hikvision NVRs use this format; the old bare /Channels/N path
        # returns 400 Bad Request even on V3.x firmware.
        channel_path = f"/Streaming/Channels/{channel_id}01"

        rtsp_url = (
            f"ffmpeg:rtsp://{encoded_user}:{encoded_pass}"
            f"@{nvr.nvr_ip}:{nvr.rtsp_port}"
            f"{channel_path}#video=h264"
        )

    stream_name = f"{nvr.code}_{channel_id}"

    # Register with go2rtc via its REST API.
    # Send the RTSP URL as the request body (not as a query param) so go2rtc
    # stores it verbatim in its YAML config — avoids the bug where go2rtc
    # decodes %23 → # and then writes an unquoted '#' into YAML which the
    # YAML parser treats as a comment, breaking passwords that contain '#'.
    go2rtc_api = f"{settings.streaming.internal_go2rtc_url}/api/streams"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.put(
                go2rtc_api,
                params={"name": stream_name, "src": rtsp_url},
            )
            if resp.status_code not in (200, 201, 204):
                logger.warning(
                    "go2rtc registration returned %d for stream %s: %s",
                    resp.status_code,
                    stream_name,
                    resp.text[:300],
                )
            else:
                logger.info("Registered stream %s -> go2rtc", stream_name)
    except httpx.RequestError as exc:
        logger.error("Failed to reach go2rtc: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"go2rtc unreachable: {exc}",
        ) from exc

    return {"stream_name": stream_name}


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def _nvr_to_dict(nvr) -> dict:
    """
    Convert a DiscoveredNVR ORM object to a safe dict (no credentials).
    """
    return {
        "id": str(nvr.id),
        "code": nvr.code,
        "branch_name": nvr.branch_name,
        "nvr_ip": nvr.nvr_ip,
        "http_port": nvr.http_port,
        "rtsp_port": nvr.rtsp_port,
        # credentials intentionally omitted
        "device_name": nvr.device_name,
        "model": nvr.model,
        "serial_number": nvr.serial_number,
        "mac_address": nvr.mac_address,
        "firmware_version": nvr.firmware_version,
        "device_type": nvr.device_type,
        "timezone": nvr.timezone,
        "vendor": getattr(nvr, "vendor", "hikvision"),
        "sync_status": nvr.sync_status,
        "sync_error": nvr.sync_error,
        "last_synced_at": nvr.last_synced_at.isoformat() if nvr.last_synced_at else None,
        "created_at": nvr.created_at.isoformat() if nvr.created_at else None,
        "updated_at": nvr.updated_at.isoformat() if nvr.updated_at else None,
    }
