import logging
import sys
import webbrowser
from pathlib import Path

from app.core.config import settings
from app.core.security import generate_otp
from app.emails.service import (
    EmailSendError,
    send_password_reset_otp_email,
    send_verification_otp_email,
)
from app.emails.templates import (
    build_password_reset_otp_email,
    build_verification_otp_email,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PREVIEW_DIR = Path("email_previews")
PREVIEW_DIR.mkdir(exist_ok=True)

normal_name = "Muhammad Burhan"

# A malicious "name" someone could type into the sign-up form
malicious_name = '<a href="https://evil-site.example">Your account is locked, click here</a>'

previews = {
    "verification.html": build_verification_otp_email(normal_name, generate_otp()),
    "password_reset.html": build_password_reset_otp_email(normal_name, generate_otp()),
    "malicious_name.html": build_verification_otp_email(malicious_name, generate_otp()),
}

for filename, content in previews.items():
    print("=" * 60)
    print("File:   ", filename)
    print("Subject:", content.subject)
    print("-" * 60)
    print(content.text_body)

    path = PREVIEW_DIR / filename
    path.write_text(content.html_body, encoding="utf-8")
    webbrowser.open(path.resolve().as_uri())

print("=" * 60)
print(f"HTML previews saved in: {PREVIEW_DIR.resolve()}")

# Only send real emails if --send was given
if "--send" in sys.argv:
    recipient = settings.smtp_username
    print(f"\nSending both OTP emails to {recipient} ...")
    try:
        send_verification_otp_email(recipient, normal_name, generate_otp())
        send_password_reset_otp_email(recipient, normal_name, generate_otp())
    except EmailSendError as exc:
        print("FAILED:", exc, "| Original error:", repr(exc.__cause__))
        sys.exit(1)
    print("Both emails sent. Check your inbox (and spam folder).")
else:
    print("\nPreview only. Run again with --send to send real emails.")