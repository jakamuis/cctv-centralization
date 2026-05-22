from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class DatabaseSettings(BaseSettings):
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

    @property
    def database_url(self) -> str:
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

    model_config = SettingsConfigDict(
        env_prefix="STREAMING_",
        env_file=".env",
        extra="ignore"
    )


class SecuritySettings(BaseSettings):
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        extra="ignore"
    )


class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()
    backend: BackendSettings = BackendSettings()
    frontend: FrontendSettings = FrontendSettings()
    streaming: StreamingSettings = StreamingSettings()
    security: SecuritySettings = SecuritySettings()

    allowed_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()