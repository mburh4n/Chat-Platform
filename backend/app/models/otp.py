from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Only imported for type hints, to avoid a circular import at runtime
if TYPE_CHECKING:
    from app.models.user import User


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Links this OTP to a user; deleting the user deletes their OTPs
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # Only the hash of the code is stored, never the plain 6 digits
    otp_hash: Mapped[str] = mapped_column(String(255))

    # Required: every OTP must have an expiry time
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Prevents reuse of a code after it has been used once
    is_used: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # Counts wrong guesses to block brute-force attempts
    attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Python-side link: otp.user gives the User object
    user: Mapped["User"] = relationship(back_populates="email_otps")

    def __repr__(self) -> str:
        return f"<EmailOTP id={self.id} user_id={self.user_id} is_used={self.is_used}>"


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    otp_hash: Mapped[str] = mapped_column(String(255))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    is_used: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="password_reset_otps")

    def __repr__(self) -> str:
        return (
            f"<PasswordResetOTP id={self.id} user_id={self.user_id} "
            f"is_used={self.is_used}>"
        )