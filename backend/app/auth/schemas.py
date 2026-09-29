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
