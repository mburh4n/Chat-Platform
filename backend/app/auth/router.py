from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.schemas import ErrorResponse, MessageResponse
from app.emails.service import (
    safe_send,
    send_password_reset_otp_email,
    send_verification_otp_email,
)
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# One shared message, so every resend response is identical
RESEND_VERIFICATION_MESSAGE = (
    "If this email belongs to an account that still needs verification, "
    "a new code has been sent."
)
FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for this email, a password reset code has been sent."
)


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


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ResendOTPRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Send a new verification code.

    Always returns the same message, whether or not the email is registered,
    so it can't be used to discover accounts.
    """
    result = auth_service.resend_verification_code(db, payload)

    if result is not None:
        user, code = result
        background_tasks.add_task(
            safe_send,
            send_verification_otp_email,
            to_email=user.email,
            name=user.name,
            otp=code,
        )

    # Identical response in every case
    return MessageResponse(message=RESEND_VERIFICATION_MESSAGE)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        403: {"model": ErrorResponse, "description": "Email not verified yet"},
    },
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Log in with email and password and receive a JWT access token."""
    access_token = auth_service.login(db, payload)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    responses={401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"}},
)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Log out everywhere: every token issued so far stops working."""
    auth_service.logout(db, current_user)
    return MessageResponse(message="You have been logged out.")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Email a password reset code.

    Always returns the same message, whether or not the email is registered.
    """
    result = auth_service.request_password_reset(db, payload)

    if result is not None:
        user, code = result
        background_tasks.add_task(
            safe_send,
            send_password_reset_otp_email,
            to_email=user.email,
            name=user.name,
            otp=code,
        )

    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid, expired, or incorrect code"},
        429: {"model": ErrorResponse, "description": "Too many incorrect attempts"},
    },
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Choose a new password using the 6-digit code from the reset email."""
    auth_service.reset_password(db, payload)
    return MessageResponse(message="Your password has been reset. You can now log in.")
