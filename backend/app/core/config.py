from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class DatabaseSettings(BaseSettings):
    database_url: Optional[str] = None
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "cctv_db"
    environment: str = "local"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def resolved_host(self) -> str:
        if self.environment == "docker":
            return "postgres"
        return self.postgres_host

    def get_database_url(self) -> str:
        # Prioritize DATABASE_URL environment variable
        if self.database_url:
            return self.database_url
        # Fallback to constructed URL
        return (
            f"postgresql+asyncpg://"
            f"{self.postgres_user}:"
            f"{self.postgres_password}@"
            f"{self.resolved_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )


class BackendSettings(BaseSettings):
    backend_port: int = 8000

    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=".env",
        extra="ignore"
    )


class FrontendSettings(BaseSettings):
    vite_backend_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_prefix="FRONTEND_",
        env_file=".env",
        extra="ignore"
    )


class StreamingSettings(BaseSettings):
    go2rtc_http_address: str = ":1984"
    go2rtc_host: str = "go2rtc"

    # Public-facing base URL for go2rtc that the browser can reach.
    # In local dev this is http://localhost:1984
    # In Docker/production set STREAMING_GO2RTC_PUBLIC_URL accordingly.
    go2rtc_public_url: str = "http://localhost:1984"

    # Internal backend→go2rtc API base URL.
    # Set STREAMING_GO2RTC_API_URL in .env to override.
    # Defaults to None — falls back to http://{go2rtc_host}:{port}
    go2rtc_api_url: Optional[str] = None

    idle_timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_prefix="STREAMING_",
        env_file=".env",
        extra="ignore"
    )

    @property
    def internal_go2rtc_url(self) -> str:
        """
        Base URL the backend uses to call go2rtc REST API.

        Priority:
          1. STREAMING_GO2RTC_API_URL  (explicit override — recommended for local dev)
          2. http://{go2rtc_host}:{port}  (constructed from host + address)
        """
        if self.go2rtc_api_url:
            return self.go2rtc_api_url.rstrip("/")
        port = self.go2rtc_http_address.lstrip(":") or "1984"
        return f"http://{self.go2rtc_host}:{port}"


class SecuritySettings(BaseSettings):
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    # Stream token specific settings
    stream_token_secret: Optional[str] = None
    stream_token_algorithm: str = "HS256"
    stream_token_expire_seconds: int = 300  # 5 minutes default

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        extra="ignore"
    )


class DiscoverySettings(BaseSettings):
    """
    Settings for Phase 7B — Seeded Hikvision Auto Discovery.

    All values can be overridden via environment variables with the
    DISCOVERY_ prefix (e.g. DISCOVERY_CSV_URL=https://...).
    """

    # Google Sheet CSV export URL — single source of truth for NVR seeds.
    # Override this in .env or Docker environment to point at a different sheet.
    csv_url: str = (
        "https://docs.google.com/spreadsheets/d/"
        "1_agN2NJL1e08umdeNUupu8Y0GXR2PMgQGYVmNwPCDZs"
        "/export?format=csv"
    )

    # HTTP timeout (seconds) when fetching the CSV
    csv_fetch_timeout: float = 30.0

    # HTTP connect timeout (seconds) when probing NVRs via ISAPI
    isapi_connect_timeout: float = 10.0

    # HTTP read timeout (seconds) for ISAPI device-info calls
    isapi_read_timeout: float = 20.0

    # HTTP read timeout (seconds) for ISAPI channel-list calls (can be large)
    isapi_channel_timeout: float = 30.0

    model_config = SettingsConfigDict(
        env_prefix="DISCOVERY_",
        env_file=".env",
        extra="ignore",
    )


class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()
    backend: BackendSettings = BackendSettings()
    frontend: FrontendSettings = FrontendSettings()
    streaming: StreamingSettings = StreamingSettings()
    discovery: DiscoverySettings = DiscoverySettings()

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    security: SecuritySettings = SecuritySettings()

    allowed_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()