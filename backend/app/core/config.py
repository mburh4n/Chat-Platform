from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py is in backend/app/core/, so the project root is three folders up
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Application
    app_name: str = "PDF Chat Platform"

    # Database (required)
    database_url: str

    # OTP settings
    otp_secret_key: str = Field(min_length=32)  # required, must be long and random
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5

    # JWT settings
    jwt_secret_key: str = Field(min_length=32)  # required, different from the OTP key
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # Email (Gmail SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: EmailStr
    smtp_password: SecretStr
    smtp_from_email: EmailStr
    smtp_from_name: str = "PDF Chat Platform"
    smtp_timeout_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore .env values that are meant for Docker, not this class
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()