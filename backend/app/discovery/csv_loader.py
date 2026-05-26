"""
discovery/csv_loader.py

Downloads and parses the Google Sheet CSV that acts as the single source
of truth for NVR device seeds.

Why this file exists:
  - Isolates all I/O related to fetching the CSV from the rest of the pipeline.
  - Handles network errors, malformed CSV, and missing columns gracefully.
  - Returns a list of CsvDeviceRow objects so the sync engine works with
    typed data, not raw dicts.

Design decisions:
  - Uses httpx (already in requirements.txt) for async HTTP.
  - A configurable timeout prevents the sync from hanging indefinitely.
  - Each row is parsed independently; a bad row is logged and skipped rather
    than aborting the entire load.
  - Column names are normalised (lowercased, stripped) so minor formatting
    differences in the sheet header don't break the parser.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import List, Tuple

import httpx
from pydantic import ValidationError

from app.discovery.schemas import CsvDeviceRow

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The Google Sheet export URL — override via DISCOVERY_CSV_URL env var
# (see config.py extension below).  We keep a module-level default so the
# loader works even without the env var during development.
DEFAULT_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1_agN2NJL1e08umdeNUupu8Y0GXR2PMgQGYVmNwPCDZs"
    "/export?format=csv"
)

# Seconds to wait for the Google Sheets HTTP response
CSV_FETCH_TIMEOUT_SECONDS = 30

# Expected column names (after normalisation).  Any sheet that contains at
# least these columns will be accepted; extra columns are ignored.
REQUIRED_COLUMNS = {"site_code", "nvr_ip", "username", "password", "enabled"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_csv_rows(
    csv_url: str = DEFAULT_CSV_URL,
    timeout: float = CSV_FETCH_TIMEOUT_SECONDS,
) -> Tuple[List[CsvDeviceRow], List[str]]:
    """
    Download the Google Sheet CSV and return parsed rows.

    Parameters
    ----------
    csv_url : str
        Full URL to the CSV export endpoint.
    timeout : float
        HTTP request timeout in seconds.

    Returns
    -------
    rows : List[CsvDeviceRow]
        Successfully parsed rows (may include disabled rows — callers decide
        whether to skip them).
    errors : List[str]
        Human-readable error messages for rows that could not be parsed.
        These are informational; the caller should log them.

    Raises
    ------
    RuntimeError
        If the HTTP request itself fails (network error, non-200 status, etc.).
        The sync engine catches this and marks the entire sync as failed.
    """

    logger.info("Fetching device seed CSV from: %s", csv_url)

    raw_text = await _download_csv(csv_url, timeout)

    rows, errors = _parse_csv_text(raw_text)

    logger.info(
        "CSV loaded: %d rows parsed, %d parse errors",
        len(rows),
        len(errors),
    )

    return rows, errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _download_csv(url: str, timeout: float) -> str:
    """
    Perform the async HTTP GET and return the response body as a string.

    Raises RuntimeError on any HTTP or network failure so the caller can
    surface a clean error message without exposing httpx internals.
    """

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            logger.debug(
                "CSV fetch successful: HTTP %d, content-length=%s",
                response.status_code,
                response.headers.get("content-length", "unknown"),
            )
            return response.text

    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"Timed out fetching CSV after {timeout}s: {exc}"
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"HTTP {exc.response.status_code} fetching CSV from {url}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            f"Network error fetching CSV: {exc}"
        ) from exc


def _parse_csv_text(
    raw_text: str,
) -> Tuple[List[CsvDeviceRow], List[str]]:
    """
    Parse the raw CSV string into a list of CsvDeviceRow objects.

    Strategy:
      1. Use csv.DictReader so column order doesn't matter.
      2. Normalise header names (strip + lowercase) to tolerate minor
         formatting differences in the Google Sheet.
      3. Validate required columns are present before iterating rows.
      4. Parse each row with Pydantic; catch ValidationError per row so
         one bad row never aborts the whole load.

    Returns (rows, errors) where errors is a list of human-readable strings.
    """

    rows: List[CsvDeviceRow] = []
    errors: List[str] = []

    # Strip UTF-8 BOM if present (exported from Excel / Google Sheets)
    raw_text = raw_text.lstrip("﻿")

    # Auto-detect delimiter: use semicolon if first header line contains ';'
    first_line = raw_text.splitlines()[0] if raw_text.strip() else ""
    delimiter = ";" if ";" in first_line else ","

    reader = csv.DictReader(io.StringIO(raw_text), delimiter=delimiter)

    if reader.fieldnames is None:
        errors.append("CSV appears to be empty — no header row found")
        return rows, errors

    # Normalise header names
    normalised_headers = {
        col.strip().lower(): col
        for col in reader.fieldnames
        if col  # skip None / empty fieldnames
    }

    # Check required columns exist
    missing = REQUIRED_COLUMNS - set(normalised_headers.keys())
    if missing:
        errors.append(
            f"CSV is missing required columns: {sorted(missing)}. "
            f"Found columns: {sorted(normalised_headers.keys())}"
        )
        return rows, errors

    logger.debug("CSV columns detected: %s", list(normalised_headers.keys()))

    for line_number, raw_row in enumerate(reader, start=2):  # start=2: row 1 is header
        # Re-key the row using normalised column names
        normalised_row = {
            norm_key: raw_row.get(orig_key, "")
            for norm_key, orig_key in normalised_headers.items()
        }

        # Skip completely blank rows (all values empty)
        if not any(v.strip() for v in normalised_row.values()):
            logger.debug("Line %d: skipping blank row", line_number)
            continue

        try:
            row = CsvDeviceRow(**normalised_row)
            rows.append(row)
            logger.debug(
                "Line %d: parsed row site_code=%r nvr_ip=%r enabled=%r",
                line_number,
                row.site_code,
                row.nvr_ip,
                row.enabled,
            )

        except ValidationError as exc:
            msg = (
                f"Line {line_number}: validation error — "
                f"{exc.error_count()} issue(s): "
                + "; ".join(
                    f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
                    for e in exc.errors()
                )
            )
            errors.append(msg)
            logger.warning(msg)

        except Exception as exc:  # noqa: BLE001
            msg = f"Line {line_number}: unexpected parse error — {exc}"
            errors.append(msg)
            logger.warning(msg)

    return rows, errors
