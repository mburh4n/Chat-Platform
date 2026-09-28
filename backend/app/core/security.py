from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

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