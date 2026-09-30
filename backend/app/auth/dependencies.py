from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.models import User

# HTTPBearer makes Swagger show an "Authorize" button where a token can be pasted.
# auto_error=False lets us raise our own 401 with a consistent {"detail": ...} body.
bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token from /api/auth/login")

INVALID_TOKEN_MESSAGE = "Invalid or expired token. Please log in again."


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the logged-in user, or raise 401.

    A token is only accepted if:
    - its signature, expiry and type are valid,
    - the user still exists and is verified,
    - its "tv" (token version) matches the user's current token_version.
      Logout, password change and password reset increase token_version,
      so every token issued before them stops working immediately.
    """
    if credentials is None:
        raise UnauthorizedError("Not authenticated.")

    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        raise UnauthorizedError(INVALID_TOKEN_MESSAGE)

    user = db.get(User, token_data.user_id)
    if user is None or not user.is_verified:
        raise UnauthorizedError(INVALID_TOKEN_MESSAGE)

    if token_data.token_version != user.token_version:
        raise UnauthorizedError(INVALID_TOKEN_MESSAGE)

    return user
