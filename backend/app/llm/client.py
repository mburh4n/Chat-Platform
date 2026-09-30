from functools import lru_cache

from google import genai

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError


@lru_cache
def _create_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def get_gemini_client() -> genai.Client:
    """Return the shared Gemini client (one per process, reused for every call)."""
    api_key = settings.gemini_api_key.get_secret_value()
    if not api_key:
        raise ServiceUnavailableError(
            "The AI service is not configured. Set GEMINI_API_KEY in the .env file."
        )
    return _create_client(api_key)
