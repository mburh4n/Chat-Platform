from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import TokenResponse
from app.core.config import settings
from app.core.database import get_db
from app.core.schemas import ErrorResponse
from app.models import User
from app.users import service as users_service
from app.users.schemas import ChangePasswordRequest, UpdateProfileRequest, UserResponse

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    responses={401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"}},
)


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the logged-in user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update the logged-in user's name."""
    return users_service.update_profile(db, current_user, payload)


@router.post(
    "/me/change-password",
    response_model=TokenResponse,
    responses={400: {"model": ErrorResponse, "description": "Current password is incorrect"}},
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Change the password. All existing tokens stop working; a new one is returned."""
    access_token = users_service.change_password(db, current_user, payload)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
