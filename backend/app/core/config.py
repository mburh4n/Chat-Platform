from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py is in backend/app/core/, so the project root is three folders up
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Optional: has a default value
    app_name: str = "PDF Chat Platform"

    # Required: the app will not start without it
    database_url: str

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()