"""
discovery/sync_engine.py

The core orchestrator for Phase 7B — Seeded Hikvision Auto Discovery.

Why this file exists:
  - Ties together the CSV loader, ISAPI client, and repository into a single
    pipeline that can be triggered by the API endpoint.
  - Enforces error isolation: a failure on one device never aborts the sync
    for other devices.
  - Provides structured logging at every step so operators can diagnose
    issues without reading raw stack traces.

Pipeline per device:
  1. Validate the CSV row (required fields, IP format).
  2. Open an ISAPI client session.
  3. Fetch /ISAPI/System/deviceInfo  → connectivity probe + device metadata.
  4. Fetch IP channels (InputProxy/channels).
  5. If no IP channels, fall back to analog channels.
  6. Upsert the NVR row in PostgreSQL.
  7. Replace the channel list in PostgreSQL.
  8. Commit the transaction.
  9. Record the outcome in DeviceSyncResult.

Error handling:
  - ISAPIConnectionError  → status "unreachable"
  - ISAPIAuthError        → status "auth_error"
  - Any other exception   → status "failed"
  - In all error cases the NVR row is still upserted with the error status
    so the UI can show which devices are problematic.

Design decisions:
  - Devices are processed sequentially (not concurrently) to avoid
    overwhelming NVRs that have limited HTTP connection pools.
  - The CSV URL is read from settings so it can be overridden per environment
    without code changes.
  - The session is passed in from the FastAPI dependency so the engine is
    fully testable without a real database.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.discovery.csv_loader import fetch_csv_rows
from app.discovery.isapi_client import (
    HikvisionISAPIClient,
    ISAPIAuthError,
    ISAPIConnectionError,
    ISAPIResponseError,
)
from app.discovery.acti_client import (
    ActiSNVRClient,
    ActiAuthError,
    ActiConnectionError,
    ActiResponseError,
)
from app.discovery.uniview_client import (
    UniviewNVRClient,
    UniviewAuthError,
    UniviewConnectionError,
    UniviewResponseError,
)
from app.discovery.schemas import (
    CsvDeviceRow,
    DeviceSyncResult,
    HikvisionDeviceInfo,
    ActiDeviceInfo,
    SyncResponse,
)
from app.repositories.discovery import DiscoveryRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_sync(
    db: AsyncSession,
    csv_url: Optional[str] = None,
) -> SyncResponse:
    """
    Execute the full discovery sync pipeline.

    Parameters
    ----------
    db : AsyncSession
        SQLAlchemy async session (injected by FastAPI).
    csv_url : str, optional
        Override the Google Sheet CSV URL.  Defaults to the URL baked into
        csv_loader.DEFAULT_CSV_URL (or the DISCOVERY_CSV_URL env var).

    Returns
    -------
    SyncResponse
        Structured summary of the sync run.
    """

    logger.info("=== Discovery sync started ===")

    # ------------------------------------------------------------------
    # 1. Load CSV
    # ------------------------------------------------------------------

    from app.discovery.csv_loader import DEFAULT_CSV_URL
    effective_url = csv_url or _get_csv_url_from_settings() or DEFAULT_CSV_URL

    try:
        rows, parse_errors = await fetch_csv_rows(csv_url=effective_url)
    except RuntimeError as exc:
        # Network / HTTP failure fetching the CSV — abort the whole sync
        logger.error("Failed to fetch CSV: %s", exc)
        raise

    if parse_errors:
        for err in parse_errors:
            logger.warning("CSV parse warning: %s", err)

    total_rows = len(rows)
    enabled_rows = [r for r in rows if r.is_enabled]

    logger.info(
        "CSV: %d total rows, %d enabled, %d disabled/skipped",
        total_rows,
        len(enabled_rows),
        total_rows - len(enabled_rows),
    )

    # ------------------------------------------------------------------
    # 2. Process each enabled device
    # ------------------------------------------------------------------

    results: List[DeviceSyncResult] = []
    synced_count = 0
    skipped_count = 0
    failed_count = 0

    # Count disabled rows as skipped upfront
    for row in rows:
        if not row.is_enabled:
            results.append(
                DeviceSyncResult(
                    code=row.code,
                    nvr_ip=row.nvr_ip or "(unknown)",
                    http_port=row.http_port_int,
                    status="skipped",
                    reason="Row disabled in CSV (enabled=false)",
                )
            )
            skipped_count += 1

    for row in enabled_rows:
        result = await _sync_single_device(db, row)
        results.append(result)

        if result.status == "synced":
            synced_count += 1
        elif result.status == "skipped":
            skipped_count += 1
        else:
            failed_count += 1

    logger.info(
        "=== Discovery sync complete: synced=%d skipped=%d failed=%d ===",
        synced_count, skipped_count, failed_count,
    )

    return SyncResponse(
        total_rows=total_rows,
        enabled_rows=len(enabled_rows),
        synced=synced_count,
        skipped=skipped_count,
        failed=failed_count,
        results=results,
    )


# ---------------------------------------------------------------------------
# Per-device sync
# ---------------------------------------------------------------------------

async def _sync_single_device(
    db: AsyncSession,
    row: CsvDeviceRow,
) -> DeviceSyncResult:
    """
    Sync one CSV row: validate → probe ISAPI → persist → return result.

    This function NEVER raises — all exceptions are caught and converted
    into a DeviceSyncResult with status "failed" / "unreachable" / "auth_error".
    """

    code = row.code
    nvr_ip = row.nvr_ip or "(unknown)"
    http_port = row.http_port_int

    logger.info("Syncing device: code=%s ip=%s port=%d", code, nvr_ip, http_port)

    # ------------------------------------------------------------------
    # Step A: Validate the row
    # ------------------------------------------------------------------

    valid, reason = row.is_valid_for_sync()
    if not valid:
        logger.warning("Skipping %s/%s — %s", code, nvr_ip, reason)
        return DeviceSyncResult(
            code=code,
            nvr_ip=nvr_ip,
            http_port=http_port,
            status="skipped",
            reason=reason,
        )

    # ------------------------------------------------------------------
    # Step B: vendor-specific connectivity + device info
    # ------------------------------------------------------------------

    device_info = None
    channels = []
    sync_status = "failed"
    sync_error: Optional[str] = None

    if row.vendor_str == "acti_snvr":
        try:
            async with ActiSNVRClient(
                ip=row.nvr_ip,          # type: ignore[arg-type]
                port=http_port,
                username=row.username,  # type: ignore[arg-type]
                password=row.password,  # type: ignore[arg-type]
            ) as client:

                logger.debug("Probing ACTi SNVR for %s:%d", nvr_ip, http_port)
                device_info = await client.get_device_info()
                logger.info(
                    "ACTi device OK: site=%s ip=%s",
                    code, nvr_ip,
                )

                channels = await client.get_channels()
                logger.info(
                    "ACTi channels found: site=%s ip=%s count=%d",
                    code, nvr_ip, len(channels),
                )
                sync_status = "synced"

        except ActiConnectionError as exc:
            sync_status = "unreachable"
            sync_error = str(exc)
            logger.warning("ACTi unreachable: site=%s ip=%s — %s", code, nvr_ip, exc)

        except ActiAuthError as exc:
            sync_status = "auth_error"
            sync_error = str(exc)
            logger.warning("ACTi auth failed: site=%s ip=%s — %s", code, nvr_ip, exc)

        except ActiResponseError as exc:
            sync_status = "failed"
            sync_error = str(exc)
            logger.error("ACTi response error: site=%s ip=%s — %s", code, nvr_ip, exc)

        except Exception as exc:  # noqa: BLE001
            sync_status = "failed"
            sync_error = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "Unexpected error syncing ACTi site=%s ip=%s", code, nvr_ip
            )

    elif row.vendor_str == "uniview":
        try:
            async with UniviewNVRClient(
                ip=row.nvr_ip,          # type: ignore[arg-type]
                port=http_port,
                rtsp_port=row.rtsp_port_int,
                username=row.username,  # type: ignore[arg-type]
                password=row.password,  # type: ignore[arg-type]
            ) as client:

                logger.debug("Probing Uniview NVR for %s:%d", nvr_ip, http_port)
                device_info = await client.get_device_info()
                logger.info(
                    "Uniview device OK: site=%s ip=%s model=%s serial=%s",
                    code, nvr_ip,
                    device_info.model,
                    device_info.serial_number,
                )

                channels = await client.get_channels()
                logger.info(
                    "Uniview channels found: site=%s ip=%s count=%d",
                    code, nvr_ip, len(channels),
                )
                sync_status = "synced"

        except UniviewConnectionError as exc:
            sync_status = "unreachable"
            sync_error = str(exc)
            logger.warning("Uniview unreachable: site=%s ip=%s — %s", code, nvr_ip, exc)

        except UniviewAuthError as exc:
            sync_status = "auth_error"
            sync_error = str(exc)
            logger.warning("Uniview auth failed: site=%s ip=%s — %s", code, nvr_ip, exc)

        except UniviewResponseError as exc:
            sync_status = "failed"
            sync_error = str(exc)
            logger.error("Uniview response error: site=%s ip=%s — %s", code, nvr_ip, exc)

        except Exception as exc:  # noqa: BLE001
            sync_status = "failed"
            sync_error = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "Unexpected error syncing Uniview site=%s ip=%s", code, nvr_ip
            )

    else:
        # Default: Hikvision ISAPI
        try:
            async with HikvisionISAPIClient(
                ip=row.nvr_ip,          # type: ignore[arg-type]
                port=http_port,
                username=row.username,  # type: ignore[arg-type]
                password=row.password,  # type: ignore[arg-type]
            ) as client:

                logger.debug("Fetching deviceInfo for %s:%d", nvr_ip, http_port)
                device_info = await client.get_device_info()
                logger.info(
                    "Device info OK: site=%s ip=%s model=%s serial=%s firmware=%s",
                    code, nvr_ip,
                    device_info.model,
                    device_info.serial_number,
                    device_info.firmware_version,
                )

                channels = await client.get_ip_channels()

                if not channels:
                    logger.debug(
                        "No IP channels found for %s:%d, trying analog channels",
                        nvr_ip, http_port,
                    )
                    channels = await client.get_analog_channels()

                logger.info(
                    "Channels found: site=%s ip=%s count=%d",
                    code, nvr_ip, len(channels),
                )
                sync_status = "synced"

        except ISAPIConnectionError as exc:
            sync_status = "unreachable"
            sync_error = str(exc)
            logger.warning("Device unreachable: site=%s ip=%s — %s", code, nvr_ip, exc)

        except ISAPIAuthError as exc:
            sync_status = "auth_error"
            sync_error = str(exc)
            logger.warning("Auth failed: site=%s ip=%s — %s", code, nvr_ip, exc)

        except ISAPIResponseError as exc:
            sync_status = "failed"
            sync_error = str(exc)
            logger.error("ISAPI error: site=%s ip=%s — %s", code, nvr_ip, exc)

        except Exception as exc:  # noqa: BLE001
            sync_status = "failed"
            sync_error = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "Unexpected error syncing site=%s ip=%s", code, nvr_ip
            )

    # ------------------------------------------------------------------
    # Step C: Persist to database (even on failure, to record the status)
    # ------------------------------------------------------------------

    channels_saved = 0

    try:
        repo = DiscoveryRepository(db)

        nvr = await repo.upsert_nvr(
            code=code,
            branch_name=row.branch_name,
            nvr_ip=nvr_ip,
            http_port=http_port,
            rtsp_port=row.rtsp_port_int,
            username=row.username,      # type: ignore[arg-type]
            password=row.password,      # type: ignore[arg-type]
            device_info=device_info,
            sync_status=sync_status,
            sync_error=sync_error,
            vendor=row.vendor_str,
            nvr_timezone=row.timezone_str,
        )

        if sync_status == "synced" and channels:
            channels_saved = await repo.replace_channels(nvr.id, channels)

        await db.commit()

        logger.debug(
            "Persisted: site=%s ip=%s nvr_id=%s channels_saved=%d",
            code, nvr_ip, nvr.id, channels_saved,
        )

    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        db_error = f"DB error: {type(exc).__name__}: {exc}"
        logger.error(
            "Failed to persist site=%s ip=%s — %s", code, nvr_ip, db_error
        )
        return DeviceSyncResult(
            code=code,
            nvr_ip=nvr_ip,
            http_port=http_port,
            status="failed",
            reason=db_error,
        )

    # ------------------------------------------------------------------
    # Step D: Build result
    # ------------------------------------------------------------------

    return DeviceSyncResult(
        code=code,
        nvr_ip=nvr_ip,
        http_port=http_port,
        status=sync_status,
        reason=sync_error,
        device_name=device_info.device_name if device_info else None,
        model=getattr(device_info, "model", None) if device_info else None,
        serial_number=getattr(device_info, "serial_number", None) if device_info else None,
        channels_found=len(channels),
        channels_saved=channels_saved,
    )


# ---------------------------------------------------------------------------
# Settings helper
# ---------------------------------------------------------------------------

def _get_csv_url_from_settings() -> Optional[str]:
    """
    Read settings.discovery.csv_url from the application settings.

    We import settings lazily here so this module can be imported without
    triggering the full settings load (useful in unit tests).
    """
    try:
        from app.core.config import settings  # noqa: PLC0415
        return settings.discovery.csv_url
    except Exception:  # noqa: BLE001
        return None
