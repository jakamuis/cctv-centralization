from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "CCTV Centralization Backend"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://cctv:cctvpassword@postgres:5432/cctv_db"
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()