"""
discovery/schemas.py

Pydantic models for the discovery pipeline.

Why this file exists:
  - Provides strict, typed validation for every CSV row coming from Google Sheets.
  - Separates the raw CSV shape (CsvDeviceRow) from the validated, enriched
    device record (ValidatedDevice) that the sync engine works with.
  - SyncResult / DeviceSyncResult give the API endpoint a clean, structured
    response so callers know exactly what happened per device.

Design decisions:
  - All fields are Optional at the CSV level because CSV cells can be blank.
  - Validators coerce types and strip whitespace so downstream code never
    has to deal with raw strings.
  - `enabled` is parsed leniently: "true", "1", "yes" all map to True.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, field_validator, model_validator
import re


# ---------------------------------------------------------------------------
# Raw CSV row — mirrors the Google Sheet columns exactly
# ---------------------------------------------------------------------------

class CsvDeviceRow(BaseModel):
    """
    Represents one raw row from the Google Sheet CSV.

    All fields are Optional[str] because CSV cells may be empty.
    Validators clean and coerce values before the sync engine uses them.
    """

    site_code: Optional[str] = None
    branch_name: Optional[str] = None
    nvr_ip: Optional[str] = None
    http_port: Optional[str] = None
    rtsp_port: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: Optional[str] = None
    notes: Optional[str] = None
    vendor: Optional[str] = None   # "hikvision" (default) | "acti_snvr"

    # ---- field-level cleaners ----

    @field_validator("site_code", "branch_name", "nvr_ip", "username", "notes", "vendor", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        if isinstance(v, str):
            return v.strip() or None
        return v

    @field_validator("http_port", "rtsp_port", mode="before")
    @classmethod
    def strip_port(cls, v):
        if isinstance(v, str):
            return v.strip() or None
        return v

    @field_validator("password", mode="before")
    @classmethod
    def strip_password(cls, v):
        # Do NOT log or expose the password; just strip whitespace
        if isinstance(v, str):
            return v.strip() or None
        return v

    @field_validator("enabled", mode="before")
    @classmethod
    def normalise_enabled(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    # ---- computed helpers ----

    @property
    def is_enabled(self) -> bool:
        """Return True when the enabled column is a truthy value."""
        return self.enabled in ("true", "1", "yes", "y", "on")

    @property
    def http_port_int(self) -> int:
        """Parse http_port to int, defaulting to 80."""
        try:
            return int(self.http_port) if self.http_port else 80
        except ValueError:
            return 80

    @property
    def rtsp_port_int(self) -> int:
        """Parse rtsp_port to int, defaulting to 554."""
        try:
            return int(self.rtsp_port) if self.rtsp_port else 554
        except ValueError:
            return 554

    @property
    def vendor_str(self) -> str:
        """Normalised vendor string — defaults to 'hikvision' when blank."""
        if self.vendor:
            return self.vendor.lower().strip()
        return "hikvision"

    def is_valid_for_sync(self) -> tuple[bool, str]:
        """
        Quick sanity check before attempting ISAPI connectivity.

        Returns (True, "") when valid, or (False, reason) when not.
        """
        if not self.site_code:
            return False, "Missing site_code"
        if not self.nvr_ip:
            return False, "Missing nvr_ip"
        if not self.username:
            return False, "Missing username"
        if not self.password:
            return False, "Missing password"
        # Basic IP / hostname check — not exhaustive, just a sanity guard
        ip_pattern = re.compile(
            r"^(\d{1,3}\.){3}\d{1,3}$|"          # IPv4
            r"^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}$"  # hostname
        )
        if not ip_pattern.match(self.nvr_ip):
            return False, f"Invalid nvr_ip format: {self.nvr_ip}"
        return True, ""


# ---------------------------------------------------------------------------
# Hikvision device info — returned by ISAPI /System/deviceInfo
# ---------------------------------------------------------------------------

class HikvisionDeviceInfo(BaseModel):
    """
    Parsed subset of the Hikvision ISAPI /System/deviceInfo response.
    Fields are Optional because not all firmware versions return all fields.
    """

    device_name: Optional[str] = None
    device_id: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None
    encoder_version: Optional[str] = None
    device_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Hikvision channel — one entry from ISAPI /ContentMgmt/InputProxy/channels
# ---------------------------------------------------------------------------

class HikvisionChannel(BaseModel):
    """
    Represents a single IP channel (camera input) on the NVR.
    """

    channel_id: str                          # e.g. "1", "2"
    channel_name: Optional[str] = None       # user-defined name
    ip_address: Optional[str] = None         # camera IP
    manage_port: Optional[int] = None        # camera HTTP port
    protocol: Optional[str] = None           # "HIKVISION", "ONVIF", etc.
    enabled: bool = True


# ---------------------------------------------------------------------------
# ACTi SNVR device info — returned by connectivity probe
# ---------------------------------------------------------------------------

class ActiDeviceInfo(BaseModel):
    """
    Minimal device info for an ACTi SNVR.
    The SNVR has no machine-readable device-info API so we synthesise this.
    """

    device_name: Optional[str] = None
    device_type: str = "NVR"
    vendor: str = "acti_snvr"
    # These are None because the SNVR CGI API does not expose them
    model: Optional[str] = None
    serial_number: Optional[str] = None
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None


# ---------------------------------------------------------------------------
# ACTi SNVR channel — one entry from channel enumeration probe
# ---------------------------------------------------------------------------

class ActiChannel(BaseModel):
    """
    Represents a single camera channel on an ACTi SNVR.
    Discovered by probing /virtualcamera/channelN?media&streamid=0.
    """

    channel_id: str          # "1", "2", …
    channel_name: str        # "Channel 1", "Channel 2", …  (no name API)
    enabled: bool = True


# ---------------------------------------------------------------------------
# Per-device sync result
# ---------------------------------------------------------------------------

class DeviceSyncResult(BaseModel):
    """
    Outcome of syncing a single device row from the CSV.
    """

    site_code: str
    nvr_ip: str
    http_port: int
    status: str                              # "synced" | "skipped" | "failed"
    reason: Optional[str] = None            # populated on skip/fail
    device_name: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    channels_found: int = 0
    channels_saved: int = 0


# ---------------------------------------------------------------------------
# Overall sync response
# ---------------------------------------------------------------------------

class SyncResponse(BaseModel):
    """
    Top-level response returned by POST /api/discovery/sync.
    """

    total_rows: int
    enabled_rows: int
    synced: int
    skipped: int
    failed: int
    results: List[DeviceSyncResult]
