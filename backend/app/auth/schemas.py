from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.fields import Email, LoginPassword, NewPassword, OTPCode, PersonName


class StrictRequest(BaseModel):
    """Base for request schemas: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class SignupRequest(StrictRequest):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Muhammad Burhan",
                    "email": "muhammad.burhan@example.com",
                    "password": "StrongPass123",
                }
            ]
        }
    )

    name: PersonName
    email: Email
    password: NewPassword


class VerifyEmailRequest(StrictRequest):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "muhammad.burhan@example.com", "otp": "123456"}]}
    )

    email: Email
    otp: OTPCode


class ResendOTPRequest(StrictRequest):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "muhammad.burhan@example.com"}]}
    )

    email: Email


class LoginRequest(StrictRequest):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "muhammad.burhan@example.com", "password": "StrongPass123"}]
        }
    )

    email: Email
    password: LoginPassword


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    """Returned by login. The frontend sends the token back as: Authorization: Bearer <token>"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600,
                }
            ]
        }
    )

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds until the token expires
