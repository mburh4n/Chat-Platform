from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.fields import LoginPassword, NewPassword, PersonName


class UserResponse(BaseModel):
    """The public view of a user. Only these fields can ever leave the server.

    hashed_password and token_version are deliberately NOT included.
    """

    # Allows reading values from SQLAlchemy objects (user.name), not just dictionaries
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "Muhammad Burhan",
                    "email": "muhammad.burhan@example.com",
                    "is_verified": True,
                    "created_at": "2026-09-30T10:15:02Z",
                }
            ]
        },
    )

    id: int
    name: str
    email: str
    is_verified: bool
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    """Fields a user may change on their profile.

    The email is not editable here: changing it would need a new verification.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"name": "Muhammad Burhan"}]},
    )

    name: PersonName


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"current_password": "StrongPass123", "new_password": "EvenStronger456"}]
        },
    )

    # Login rules for the current password, so older passwords are still accepted
    current_password: LoginPassword
    new_password: NewPassword
