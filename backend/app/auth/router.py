from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.schemas import SignupRequest, VerifyEmailRequest
from app.core.database import get_db
from app.core.schemas import ErrorResponse, MessageResponse
from app.emails.service import safe_send, send_verification_otp_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# Plain "def" (not "async def") because the database session is synchronous
@router.post(
    "/signup",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        429: {"model": ErrorResponse, "description": "Code requested too recently"},
    },
)
def signup(
    payload: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Create an account and email a 6-digit verification code."""
    user, code = auth_service.register_user(db, payload)

    # Runs after the response is sent, so the user doesn't wait for Gmail
    background_tasks.add_task(
        safe_send,
        send_verification_otp_email,
        to_email=user.email,
        name=user.name,
        otp=code,
    )

    return MessageResponse(
        message="Account created. We sent a 6-digit verification code to your email."
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid, expired, or incorrect code"},
        429: {"model": ErrorResponse, "description": "Too many incorrect attempts"},
    },
)
def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Verify an email address with the 6-digit code sent at sign-up."""
    auth_service.verify_email(db, payload)
    return MessageResponse(message="Email verified successfully. You can now log in.")
