import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing (Argon2 via pwdlib)
# ---------------------------------------------------------------------------

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a salted Argon2 hash of the password. Never store the plain password."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a typed password against a stored hash."""
    try:
        return password_hash.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False


# ---------------------------------------------------------------------------
# One-time passwords (OTPs)
# ---------------------------------------------------------------------------

class OTPPurpose(StrEnum):
    """What an OTP is for. Codes for one purpose can never be used for another."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


def generate_otp() -> str:
    """Return a cryptographically secure 6-digit code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str, user_id: int, purpose: OTPPurpose) -> str:
    """Return an HMAC-SHA256 hash of the code, bound to the user and purpose."""
    message = f"{purpose}:{user_id}:{otp}".encode()
    key = settings.otp_secret_key.encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_otp(otp: str, user_id: int, purpose: OTPPurpose, otp_hash: str) -> bool:
    """Check a typed code against a stored hash."""
    expected_hash = hash_otp(otp.strip(), user_id, purpose)
    return hmac.compare_digest(expected_hash, otp_hash)


def get_otp_expiry() -> datetime:
    """Return the expiry time for a new OTP."""
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.otp_expire_minutes
    )


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AccessTokenData:
    """The verified data read from a valid access token."""

    user_id: int
    token_version: int


def create_access_token(user_id: int, token_version: int) -> str:
    """Create a signed JWT access token for a user."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "tv": token_version,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.access_token_expire_minutes
        ),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> AccessTokenData | None:
    """Verify a token and return its data, or None if it cannot be trusted."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.InvalidTokenError:
        return None

    if payload.get("type") != "access":
        return None

    try:
        return AccessTokenData(
            user_id=int(payload["sub"]),
            token_version=int(payload["tv"]),
        )
    except (KeyError, TypeError, ValueError):
        return None