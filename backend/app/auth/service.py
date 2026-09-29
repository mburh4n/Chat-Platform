import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import ResendOTPRequest, SignupRequest, VerifyEmailRequest
from app.core.exceptions import BadRequestError, ConflictError, TooManyRequestsError
from app.core.security import OTPPurpose, hash_password
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
