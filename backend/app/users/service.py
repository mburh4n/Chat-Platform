from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.users.schemas import ChangePasswordRequest, UpdateProfileRequest


def update_profile(db: Session, user: User, data: UpdateProfileRequest) -> User:
    user.name = data.name
    db.commit()
    db.refresh(user)  # loads the new updated_at set by the database
    return user


def change_password(db: Session, user: User, data: ChangePasswordRequest) -> str:
    """Change the password and return a new access token.

    token_version is increased, so every other session (other tabs, other
    devices, a stolen token) is logged out. The caller gets a fresh token
    so the current session continues.
    """
    # 400, not 401: a 401 would make the frontend think the session expired
    if not verify_password(data.current_password, user.hashed_password):
        raise BadRequestError("Current password is incorrect.")

    if verify_password(data.new_password, user.hashed_password):
        raise BadRequestError("New password must be different from the current password.")

    user.hashed_password = hash_password(data.new_password)
    user.token_version += 1
    db.commit()

    return create_access_token(user.id, user.token_version)
