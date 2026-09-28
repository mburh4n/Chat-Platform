from datetime import datetime, timezone

from app.core.security import (
    OTPPurpose,
    generate_otp,
    get_otp_expiry,
    hash_otp,
    verify_otp,
)

# 1. Generate a few codes: always 6 digits, always random
print("Five generated codes:", [generate_otp() for _ in range(5)])
print("How small numbers are formatted:", f"{42:06d}")

# 2. Hash a code for user 1
code = generate_otp()
stored_hash = hash_otp(code, user_id=1, purpose=OTPPurpose.EMAIL_VERIFICATION)
print("\nCode:", code)
print("Stored hash:", stored_hash)
print("Hash length:", len(stored_hash))

# 3. Verification
print("\nCorrect code accepted?",
      verify_otp(code, 1, OTPPurpose.EMAIL_VERIFICATION, stored_hash))
print("Correct code with a space accepted?",
      verify_otp(f" {code} ", 1, OTPPurpose.EMAIL_VERIFICATION, stored_hash))
print("Wrong code accepted?",
      verify_otp("000000" if code != "000000" else "111111",
                 1, OTPPurpose.EMAIL_VERIFICATION, stored_hash))

# 4. Binding to user and purpose
print("\nSame code, different user accepted?",
      verify_otp(code, 2, OTPPurpose.EMAIL_VERIFICATION, stored_hash))
print("Same code, used for password reset accepted?",
      verify_otp(code, 1, OTPPurpose.PASSWORD_RESET, stored_hash))

hash_user_1 = hash_otp("123456", 1, OTPPurpose.EMAIL_VERIFICATION)
hash_user_2 = hash_otp("123456", 2, OTPPurpose.EMAIL_VERIFICATION)
print("Same code for two users gives the same hash?", hash_user_1 == hash_user_2)

# 5. Expiry
now = datetime.now(timezone.utc)
expires_at = get_otp_expiry()
print("\nNow (UTC):      ", now)
print("Expires at (UTC):", expires_at)
print("Minutes until expiry:", round((expires_at - now).total_seconds() / 60))