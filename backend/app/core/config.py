from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py is in backend/app/core/, so the project root is three folders up
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Application
    app_name: str = "PDF Chat Platform"

    # Frontend origins allowed to call this API from a browser (CORS)
    cors_origins: list[str] = ["http://localhost:5173"]

    # Database (required)
    database_url: str

    # OTP settings
    otp_secret_key: str = Field(min_length=32)  # required, must be long and random
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60  # new: minimum time between new codes

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

    # Google Gemini (LLM + embeddings). Empty key: auth still works, PDF features fail clearly.
    gemini_api_key: SecretStr = SecretStr("")
    gemini_chat_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    # Tried in order when the chat model is overloaded (JSON list in .env)
    gemini_fallback_models: list[str] = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]
    # Low temperature = focused answers that stick to the retrieved text
    gemini_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # PDF uploads
    upload_dir: Path = ROOT_DIR / "backend" / "uploads"
    max_upload_size_mb: int = Field(default=20, ge=1)
    max_files_per_upload: int = Field(default=10, ge=1)

    # Chunking and retrieval
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    # MCP server (streamable HTTP endpoint)
    mcp_server_url: str = "http://localhost:8001/mcp"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore .env values that are meant for Docker, not this class
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()