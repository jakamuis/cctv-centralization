import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkey")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cctvuser:changeme@postgres:5432/cctvdb"
)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    ALLOWED_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()