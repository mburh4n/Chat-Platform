from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import TooManyRequestsError
from app.core.security import OTPPurpose, generate_otp, get_otp_expiry, hash_otp
from app.models import EmailOTP, PasswordResetOTP, User

# Which table stores OTPs for each purpose
OTP_MODELS: dict[OTPPurpose, type[EmailOTP] | type[PasswordResetOTP]] = {
    OTPPurpose.EMAIL_VERIFICATION: EmailOTP,
    OTPPurpose.PASSWORD_RESET: PasswordResetOTP,
}


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
