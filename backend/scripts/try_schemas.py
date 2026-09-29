from pydantic import ValidationError

from app.auth.schemas import (
    LoginRequest,
    ResendOTPRequest,
    SignupRequest,
    VerifyEmailRequest,
)


def check(title: str, schema, data: dict) -> None:
    """Validate data against a schema and print the result or the errors."""
    print(f"\n--- {title}")
    try:
        result = schema.model_validate(data)
        print("VALID ->", result.model_dump())
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"]) or "(request)"
            print(f"INVALID -> {field}: {error['msg']}")


# ---------------- Sign-up: valid input is cleaned ----------------
check("Valid sign-up (messy spacing and capital letters)", SignupRequest, {
    "name": "   Muhammad    Burhan  ",
    "email": "  Muhammad.Burhan@Gmail.COM ",
    "password": "StrongPass123",
})
check("Name in Urdu script is allowed", SignupRequest, {
    "name": "محمد برہان",
    "email": "muhammad.burhan@example.com",
    "password": "StrongPass123",
})

# ---------------- Sign-up: invalid input is rejected ----------------
check("Missing fields", SignupRequest, {"email": "muhammad.burhan@example.com"})
check("Invalid email", SignupRequest, {
    "name": "Muhammad Burhan", "email": "not-an-email", "password": "StrongPass123",
})
check("Name too short after cleaning", SignupRequest, {
    "name": "  A  ", "email": "muhammad.burhan@example.com", "password": "StrongPass123",
})
check("Name with a control character", SignupRequest, {
    "name": "Muhammad\u0000Burhan", "email": "muhammad.burhan@example.com", "password": "StrongPass123",
})
check("Password too short", SignupRequest, {
    "name": "Muhammad Burhan", "email": "muhammad.burhan@example.com", "password": "abc1",
})
check("Password without a number", SignupRequest, {
    "name": "Muhammad Burhan", "email": "muhammad.burhan@example.com", "password": "OnlyLetters",
})
check("Password without a letter", SignupRequest, {
    "name": "Muhammad Burhan", "email": "muhammad.burhan@example.com", "password": "12345678",
})
check("Password far too long", SignupRequest, {
    "name": "Muhammad Burhan", "email": "muhammad.burhan@example.com", "password": "a1" * 100,
})
check("Extra field trying to set is_verified", SignupRequest, {
    "name": "Muhammad Burhan", "email": "muhammad.burhan@example.com",
    "password": "StrongPass123", "is_verified": True,
})

# ---------------- Verify email ----------------
check("Valid OTP with spaces around it", VerifyEmailRequest, {
    "email": "Muhammad.Burhan@Example.com", "otp": " 048213 ",
})
check("OTP with 5 digits", VerifyEmailRequest, {"email": "muhammad.burhan@example.com", "otp": "12345"})
check("OTP with letters", VerifyEmailRequest, {"email": "muhammad.burhan@example.com", "otp": "12a456"})
check("OTP with digits from another script", VerifyEmailRequest, {
    "email": "muhammad.burhan@example.com", "otp": "۱۲۳۴۵۶",
})
check("OTP sent as a number instead of text", VerifyEmailRequest, {
    "email": "muhammad.burhan@example.com", "otp": 123456,
})

# ---------------- Resend OTP ----------------
check("Valid resend", ResendOTPRequest, {"email": " MUHAMMAD.BURHAN@example.com"})

# ---------------- Login ----------------
check("Login: weak but non-empty password is accepted", LoginRequest, {
    "email": "Muhammad.Burhan@Example.com", "password": "old",
})
check("Login: empty password", LoginRequest, {"email": "muhammad.burhan@example.com", "password": ""})
