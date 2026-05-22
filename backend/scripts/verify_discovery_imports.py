"""
Quick import verification for Phase 7B discovery module.
Run from backend/ directory: python scripts/verify_discovery_imports.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cctv_db")
os.environ.setdefault("SECURITY_JWT_SECRET_KEY", "test-secret")

errors = []

def check(label, fn):
    try:
        result = fn()
        print(f"  OK  {label}" + (f" — {result}" if result else ""))
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        errors.append((label, e))

print("=== Phase 7B Discovery Import Verification ===\n")

check("schemas: CsvDeviceRow", lambda: (
    __import__("app.discovery.schemas", fromlist=["CsvDeviceRow"]).CsvDeviceRow.__name__
))

check("schemas: SyncResponse", lambda: (
    __import__("app.discovery.schemas", fromlist=["SyncResponse"]).SyncResponse.__name__
))

check("csv_loader: DEFAULT_CSV_URL", lambda: (
    __import__("app.discovery.csv_loader", fromlist=["DEFAULT_CSV_URL"]).DEFAULT_CSV_URL[:55] + "..."
))

check("isapi_client: HikvisionISAPIClient", lambda: (
    __import__("app.discovery.isapi_client", fromlist=["HikvisionISAPIClient"]).HikvisionISAPIClient.__name__
))

check("isapi_client: exception classes", lambda: (
    str([
        __import__("app.discovery.isapi_client", fromlist=["ISAPIConnectionError"]).ISAPIConnectionError.__name__,
        __import__("app.discovery.isapi_client", fromlist=["ISAPIAuthError"]).ISAPIAuthError.__name__,
    ])
))

check("sync_engine: run_sync", lambda: (
    __import__("app.discovery.sync_engine", fromlist=["run_sync"]).run_sync.__name__
))

check("models: DiscoveredNVR table", lambda: (
    __import__("app.models.discovered_nvr", fromlist=["DiscoveredNVR"]).DiscoveredNVR.__tablename__
))

check("models: NVRChannel table", lambda: (
    __import__("app.models.nvr_channel", fromlist=["NVRChannel"]).NVRChannel.__tablename__
))

check("repository: DiscoveryRepository", lambda: (
    __import__("app.repositories.discovery", fromlist=["DiscoveryRepository"]).DiscoveryRepository.__name__
))

check("router: discovery routes", lambda: (
    str([r.path for r in __import__("app.api.v1.routers.discovery", fromlist=["router"]).router.routes])
))

check("config: settings.discovery.csv_url", lambda: (
    __import__("app.core.config", fromlist=["settings"]).settings.discovery.csv_url[:55] + "..."
))

# Validate CsvDeviceRow logic
print("\n--- CsvDeviceRow validation tests ---")
from app.discovery.schemas import CsvDeviceRow

row_enabled = CsvDeviceRow(site_code="SITE01", nvr_ip="192.168.1.100", http_port="80", rtsp_port="554", username="admin", password="pass123", enabled="true")
assert row_enabled.is_enabled is True, "enabled=true should be True"
assert row_enabled.http_port_int == 80
assert row_enabled.rtsp_port_int == 554
valid, reason = row_enabled.is_valid_for_sync()
assert valid is True, f"Should be valid: {reason}"
print("  OK  enabled row passes validation")

row_disabled = CsvDeviceRow(site_code="SITE02", nvr_ip="192.168.1.101", enabled="false")
assert row_disabled.is_enabled is False, "enabled=false should be False"
print("  OK  disabled row correctly identified")

row_missing_ip = CsvDeviceRow(site_code="SITE03", username="admin", password="pass", enabled="true")
valid, reason = row_missing_ip.is_valid_for_sync()
assert valid is False
assert "nvr_ip" in reason
print("  OK  missing nvr_ip correctly rejected:", reason)

row_bad_ip = CsvDeviceRow(site_code="SITE04", nvr_ip="not_an_ip!!!", username="admin", password="pass", enabled="true")
valid, reason = row_bad_ip.is_valid_for_sync()
assert valid is False
print("  OK  bad IP format correctly rejected:", reason)

print()
if errors:
    print(f"=== FAILED: {len(errors)} error(s) ===")
    for label, exc in errors:
        print(f"  - {label}: {exc}")
    sys.exit(1)
else:
    print("=== ALL CHECKS PASSED ===")
