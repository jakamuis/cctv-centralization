"""
Discovery package — Phase 7B: Seeded Hikvision Auto Discovery.

Architecture:
  - Google Sheet CSV is the single source of truth
  - No subnet scanning, no SADP, no ONVIF
  - Manual sync only via POST /api/discovery/sync

Sub-modules:
  csv_loader   — Downloads and parses the Google Sheet CSV
  isapi_client — Async Hikvision ISAPI HTTP client
  sync_engine  — Orchestrates the full sync pipeline
"""
