import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing (Argon2 via pwdlib)
# ---------------------------------------------------------------------------

# Created once and reused. Uses Argon2id with safe default settings.
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a salted Argon2 hash of the password. Never store the plain password."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a typed password against a stored hash.

    Returns False (instead of crashing) if the stored value is not a valid hash.
    """
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
    """Return a cryptographically secure 6-digit code, e.g. '048213'."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str, user_id: int, purpose: OTPPurpose) -> str:
    """Return an HMAC-SHA256 hash of the code, bound to the user and purpose.

    Without the secret key, stolen hashes cannot be brute-forced.
    """
    message = f"{purpose}:{user_id}:{otp}".encode()
    key = settings.otp_secret_key.encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_otp(otp: str, user_id: int, purpose: OTPPurpose, otp_hash: str) -> bool:
    """Check a typed code against a stored hash using a constant-time comparison."""
    expected_hash = hash_otp(otp.strip(), user_id, purpose)
    return hmac.compare_digest(expected_hash, otp_hash)


def get_otp_expiry() -> datetime:
    """Return the expiry time for a new OTP (timezone-aware, UTC)."""
    return datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)