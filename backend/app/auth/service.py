import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyEmailRequest,
)
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    TooManyRequestsError,
    UnauthorizedError,
)
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    OTPPurpose,
    create_access_token,
    hash_password,
    verify_password,
)
from app.emails.otp_service import INVALID_CODE_MESSAGE, consume_otp, create_otp
from app.models import User

logger = logging.getLogger(__name__)


def register_user(db: Session, data: SignupRequest) -> tuple[User, str]:
    """Create an unverified user (or restart an unverified sign-up) and a new OTP.

    Returns the user and the plain OTP code, which the caller emails.
    The user and the OTP are saved together in one transaction.
    """
    user = db.scalar(select(User).where(User.email == data.email))

    # A verified account already owns this email
    if user is not None and user.is_verified:
        raise ConflictError("An account with this email already exists. Please log in.")

    if user is None:
        # Brand-new account
        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        db.add(user)
    else:
        # Unverified account: restart sign-up with the new details
        user.name = data.name
        user.hashed_password = hash_password(data.password)

    try:
        db.flush()  # assigns user.id, needed to hash the OTP
        code = create_otp(db, user, OTPPurpose.EMAIL_VERIFICATION)
        db.commit()  # user and OTP are saved together
    except IntegrityError:
        # Two sign-ups for the same new email at the same moment:
        # the unique index on email rejected the second one
        db.rollback()
        raise ConflictError("An account with this email already exists. Please log in.")

    return user, code


def verify_email(db: Session, data: VerifyEmailRequest) -> None:
    """Verify a user's email with their OTP code.

    The code is marked as used and the user as verified in one transaction.
    """
    user = db.scalar(select(User).where(User.email == data.email))

    # Same message as a bad code, so this endpoint can't reveal which emails exist
    if user is None:
        raise BadRequestError(INVALID_CODE_MESSAGE)

    if user.is_verified:
        raise BadRequestError("This email is already verified. Please log in.")

    # Raises an error if the code can't be accepted
    consume_otp(db, user, OTPPurpose.EMAIL_VERIFICATION, data.otp)

    user.is_verified = True
    db.commit()  # saves "code used" and "user verified" together


def resend_verification_code(
    db: Session, data: ResendOTPRequest
) -> tuple[User, str] | None:
    """Create a new verification code if one is needed and allowed.

    Returns (user, code) when an email should be sent, otherwise None.
    The caller must respond the SAME way in both cases, so this endpoint
    never reveals whether an email is registered.
    """
    user = db.scalar(select(User).where(User.email == data.email))

    # Unknown or already verified: nothing to send
    if user is None or user.is_verified:
        return None

    try:
        code = create_otp(db, user, OTPPurpose.EMAIL_VERIFICATION)
    except TooManyRequestsError:
        # Cooldown is enforced silently: a 429 here would reveal the account exists
        logger.info("Verification code resend skipped for user %s: cooldown active", user.id)
        return None

    db.commit()  # saves the invalidated old codes and the new code together
    return user, code


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user if the email and password are correct, otherwise None.

    Unknown emails still run a full password check against a dummy hash,
    so both failure cases take the same time (timing-attack protection).
    """
    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)  # same work, result ignored
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def login(db: Session, data: LoginRequest) -> str:
    """Check credentials and return a JWT access token.

    Order matters: the password is checked BEFORE the verification status,
    so "please verify your email" is only shown to someone who knows the password.
    """
    user = authenticate_user(db, data.email, data.password)

    if user is None:
        # One message for both unknown email and wrong password
        raise UnauthorizedError("Invalid email or password.")

    if not user.is_verified:
        raise ForbiddenError("Please verify your email before logging in.")

    return create_access_token(user.id, user.token_version)


def logout(db: Session, user: User) -> None:
    """Invalidate every access token the user currently holds.

    JWTs can't be deleted, but each one carries the token_version it was
    issued with. Increasing it makes get_current_user reject all of them.
    """
    user.token_version += 1
    db.commit()


def request_password_reset(
    db: Session, data: ForgotPasswordRequest
) -> tuple[User, str] | None:
    """Create a password reset code if the account exists and the cooldown allows.

    Returns (user, code) when an email should be sent, otherwise None.
    The caller must respond the SAME way in both cases.
    Unverified accounts may reset too: receiving the code proves they own the email.
    """
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None:
        return None

    try:
        code = create_otp(db, user, OTPPurpose.PASSWORD_RESET)
    except TooManyRequestsError:
        # Silent, like resend-verification: a 429 would reveal the account exists
        logger.info("Password reset code skipped for user %s: cooldown active", user.id)
        return None

    db.commit()
    return user, code


def reset_password(db: Session, data: ResetPasswordRequest) -> None:
    """Set a new password using a reset code.

    In one transaction: the code is used up, the password changes, the email
    counts as verified (the code arrived in that inbox), and token_version
    increases so any session an attacker might have had is logged out.
    """
    user = db.scalar(select(User).where(User.email == data.email))

    # Same message as a bad code, so this endpoint can't reveal which emails exist
    if user is None:
        raise BadRequestError(INVALID_CODE_MESSAGE)

    consume_otp(db, user, OTPPurpose.PASSWORD_RESET, data.otp)

    user.hashed_password = hash_password(data.new_password)
    user.is_verified = True
    user.token_version += 1
    db.commit()
