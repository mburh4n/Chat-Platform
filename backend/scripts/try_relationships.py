from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import EmailOTP, User

db = SessionLocal()

try:
    user = User(
        name="Script Test",
        email="script-test@example.com",
        hashed_password="not-a-real-hash",
    )

    otp = EmailOTP(
        otp_hash="not-a-real-otp-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    # Add the OTP through the relationship instead of setting user_id by hand
    user.email_otps.append(otp)

    db.add(user)
    db.flush()  # send to the database so IDs are generated, without committing

    print("User:", user)
    print("User's OTPs:", user.email_otps)
    print("OTP belongs to:", otp.user)
    print("user_id filled in automatically:", otp.user_id == user.id)
finally:
    db.rollback()  # undo everything: this script saves nothing
    db.close()
    print("Rolled back. Nothing was saved.")