from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Only imported for type hints, to avoid a circular import at runtime
if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.otp import EmailOTP, PasswordResetOTP


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100))

    # Unique so no two accounts share an email; indexed for fast login lookups
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Only the hash is stored, never the real password
    hashed_password: Mapped[str] = mapped_column(String(255))

    # Becomes True after the user verifies their email with an OTP
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    # Incremented on logout / password change to invalidate old JWTs
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # One user -> many email verification OTPs
    email_otps: Mapped[list["EmailOTP"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One user -> many password reset OTPs
    password_reset_otps: Mapped[list["PasswordResetOTP"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One user -> many uploaded PDFs
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"