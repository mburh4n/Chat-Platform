from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, TooManyRequestsError
from app.core.security import (
    OTPPurpose,
    generate_otp,
    get_otp_expiry,
    hash_otp,
    verify_otp,
)
from app.models import EmailOTP, PasswordResetOTP, User

# Which table stores OTPs for each purpose
OTP_MODELS: dict[OTPPurpose, type[EmailOTP] | type[PasswordResetOTP]] = {
    OTPPurpose.EMAIL_VERIFICATION: EmailOTP,
    OTPPurpose.PASSWORD_RESET: PasswordResetOTP,
}

# Shared messages (also used by the auth service)
INVALID_CODE_MESSAGE = "Invalid or expired code. Please request a new one."
TOO_MANY_ATTEMPTS_MESSAGE = "Too many incorrect attempts. Please request a new code."


def create_otp(db: Session, user: User, purpose: OTPPurpose) -> str:
    """Create a new OTP for the user and return the PLAIN code (for the email only).

    - Enforces a cooldown between codes (raises TooManyRequestsError).
    - Invalidates all older unused codes for the same purpose.
    - Stores only the hash.
    - Does NOT commit: the caller decides when the transaction is saved.
    """
    model = OTP_MODELS[purpose]

    # 1. Cooldown: refuse if the newest code is too recent
    latest = db.scalar(
        select(model)
        .where(model.user_id == user.id)
        .order_by(model.created_at.desc(), model.id.desc())
        .limit(1)
    )
    if latest is not None:
        elapsed = datetime.now(timezone.utc) - latest.created_at
        cooldown = timedelta(seconds=settings.otp_resend_cooldown_seconds)
        if elapsed < cooldown:
            seconds_left = int((cooldown - elapsed).total_seconds()) + 1
            raise TooManyRequestsError(
                f"Please wait {seconds_left} seconds before requesting a new code."
            )

    # 2. Only the newest code should work: invalidate older unused ones
    db.execute(
        update(model)
        .where(model.user_id == user.id, model.is_used.is_(False))
        .values(is_used=True)
    )

    # 3. Create and store the new code (hash only)
    code = generate_otp()
    db.add(
        model(
            user_id=user.id,
            otp_hash=hash_otp(code, user.id, purpose),
            expires_at=get_otp_expiry(),
        )
    )

    # 4. Return the plain code so it can be emailed; it is never stored or logged
    return code


def consume_otp(db: Session, user: User, purpose: OTPPurpose, code: str) -> None:
    """Check a code and mark it as used. Raises an error if it can't be accepted.

    Order of checks: exists -> not expired -> attempts left -> correct code.
    Codes are never compared once expired or out of attempts.

    - Failures are committed immediately, so attempt counts are always saved.
    - Success is NOT committed: the caller commits it together with its own
      changes (e.g. marking the user as verified).
    """
    model = OTP_MODELS[purpose]

    # Newest unused code, locked so parallel guesses must wait their turn
    otp = db.scalar(
        select(model)
        .where(model.user_id == user.id, model.is_used.is_(False))
        .order_by(model.created_at.desc(), model.id.desc())
        .limit(1)
        .with_for_update()
    )

    # 1. No usable code
    if otp is None:
        raise BadRequestError(INVALID_CODE_MESSAGE)

    # 2. Expired: reject before comparing
    if otp.expires_at <= datetime.now(timezone.utc):
        otp.is_used = True
        db.commit()
        raise BadRequestError("This code has expired. Please request a new one.")

    # 3. Out of attempts: reject before comparing (safety net)
    if otp.attempts >= settings.otp_max_attempts:
        otp.is_used = True
        db.commit()
        raise TooManyRequestsError(TOO_MANY_ATTEMPTS_MESSAGE)

    # 4. Compare the code
    if not verify_otp(code, user.id, purpose, otp.otp_hash):
        otp.attempts += 1
        remaining = settings.otp_max_attempts - otp.attempts
        if remaining <= 0:
            otp.is_used = True  # last attempt used: this code is now dead
            db.commit()
            raise TooManyRequestsError(TOO_MANY_ATTEMPTS_MESSAGE)
        db.commit()  # save the attempt BEFORE returning the error
        raise BadRequestError(f"Incorrect code. {remaining} attempt(s) remaining.")

    # Correct: the code can never be used again (the caller commits)
    otp.is_used = True
