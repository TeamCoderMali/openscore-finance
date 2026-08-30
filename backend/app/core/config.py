"""
OpenScore Finance — Centralized Configuration
Uses pydantic-settings for environment variable management.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "OpenScore Finance"
    APP_VERSION: str = "1.0.0-mvp"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours for hackathon

    # Database — MySQL
    DATABASE_URL: str = "mysql+aiomysql://root:skypper19@localhost/openscore_finance"

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # File upload
    MAX_UPLOAD_SIZE_MB: int = 10
    TEMP_UPLOAD_DIR: str = "/tmp/openscore_uploads"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
