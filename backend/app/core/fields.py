"""Reusable, validated field types for request schemas.

Each type bundles its validation rules, so every endpoint that uses it
applies exactly the same rules.
"""

import unicodedata
from typing import Annotated

from pydantic import (
    AfterValidator,
    BeforeValidator,
    EmailStr,
    Field,
    StringConstraints,
)

# ---------------------------------------------------------------------------
# Email: trimmed and lowercased so each address maps to exactly one account
# ---------------------------------------------------------------------------


def _strip(value: object) -> object:
    """Remove surrounding spaces from text; leave other types for Pydantic to reject."""
    return value.strip() if isinstance(value, str) else value


def _to_lowercase(value: str) -> str:
    return value.lower()


Email = Annotated[EmailStr, BeforeValidator(_strip), AfterValidator(_to_lowercase)]


# ---------------------------------------------------------------------------
# Person name: tidy whitespace, no control characters, any language allowed
# ---------------------------------------------------------------------------


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())  # collapse spaces, tabs, and newlines
    if any(unicodedata.category(char).startswith("C") for char in cleaned):
        raise ValueError("Name contains invalid characters")
    if len(cleaned) < 2:
        raise ValueError("Name must be at least 2 characters")
    return cleaned


PersonName = Annotated[str, Field(max_length=100), AfterValidator(_clean_name)]


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def _check_password_strength(value: str) -> str:
    if not any(char.isalpha() for char in value):
        raise ValueError("Password must contain at least one letter")
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must contain at least one number")
    return value


# For choosing a password (sign-up, change, reset). Never stripped: spaces are valid.
# The maximum length prevents abuse, since password hashing is deliberately slow.
NewPassword = Annotated[
    str,
    Field(min_length=8, max_length=128),
    AfterValidator(_check_password_strength),
]

# For logging in. Strength rules are NOT applied here, so older passwords keep working.
LoginPassword = Annotated[str, Field(min_length=1, max_length=128)]


# ---------------------------------------------------------------------------
# OTP code: exactly six ASCII digits
# ---------------------------------------------------------------------------

# [0-9] instead of \d, so only the digits 0-9 are accepted
OTPCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{6}$"),
]
