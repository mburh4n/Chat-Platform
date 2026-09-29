from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.schemas import TokenResponse
from app.core.config import settings
from app.core.schemas import MessageResponse
from app.core.security import create_access_token, hash_password
from app.models import User
from app.users.schemas import UserResponse

# A User object that exists only in memory (never saved to the database)
user = User(
    id=12,
    name="Muhammad Burhan",
    email="muhammad.burhan@example.com",
    hashed_password=hash_password("StrongPass123"),
    is_verified=True,
    token_version=3,
    created_at=datetime.now(timezone.utc),
)

# ---------------------------------------------------------------------------
# Part 1: Converting objects directly
# ---------------------------------------------------------------------------
print("=== Part 1: Converting directly ===")

public_user = UserResponse.model_validate(user)  # works thanks to from_attributes=True
print("\nUserResponse as JSON:", public_user.model_dump_json(indent=2))
print("Contains 'hashed_password'?", "hashed_password" in public_user.model_dump())
print("Contains 'token_version'?", "token_version" in public_user.model_dump())

token = TokenResponse(
    access_token=create_access_token(user.id, user.token_version),
    expires_in=settings.access_token_expire_minutes * 60,
)
print("\nTokenResponse:", token.model_dump())

print("\nMessageResponse:", MessageResponse(message="Email verified successfully.").model_dump())

# ---------------------------------------------------------------------------
# Part 2: FastAPI filtering responses through response_model
# ---------------------------------------------------------------------------
print("\n=== Part 2: Through a real FastAPI app ===")

demo_app = FastAPI()


# DANGEROUS: no response_model, returns everything it's given
@demo_app.get("/unsafe")
def unsafe_endpoint():
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "hashed_password": user.hashed_password,
        "token_version": user.token_version,
    }


# SAFE: same mistake (returning extra fields), but response_model filters it
@demo_app.get("/safe-dict", response_model=UserResponse)
def safe_dict_endpoint():
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "hashed_password": user.hashed_password,  # a "mistake" that gets filtered out
        "token_version": user.token_version,
    }


# SAFE: returning the database object directly, as the Day 2 profile endpoint will
@demo_app.get("/safe-object", response_model=UserResponse)
def safe_object_endpoint():
    return user


client = TestClient(demo_app)

for path in ["/unsafe", "/safe-dict", "/safe-object"]:
    data = client.get(path).json()
    leaked = "hashed_password" in data
    print(f"\n{path}")
    print("  Fields sent:", list(data.keys()))
    print("  Password hash leaked?", "YES - DANGER" if leaked else "no")
