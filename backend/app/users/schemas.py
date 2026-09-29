from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
