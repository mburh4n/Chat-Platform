from dataclasses import dataclass
from html import escape

from app.core.config import settings


@dataclass(frozen=True)
class EmailContent:
    """The three parts of an email, ready to be sent."""

    subject: str
    text_body: str
    html_body: str
    # ---------------------------------------------------------------------------
# Shared HTML pieces (private to this file)
# ---------------------------------------------------------------------------


def _html_layout(title: str, content_html: str) -> str:
    """Wrap email content in a simple, consistent layout using inline styles."""
    app_name = escape(settings.app_name)
    safe_title = escape(title)

    return f"""<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background-color:#f4f5f7;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:480px;margin:32px auto;padding:32px;background-color:#ffffff;border-radius:8px;color:#1f2937;">
      <h1 style="margin:0 0 16px;font-size:20px;color:#111827;">{safe_title}</h1>
      {content_html}
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="margin:0;font-size:12px;color:#6b7280;">
        This is an automated message from {app_name}. Please do not reply to this email.
      </p>
    </div>
  </body>
</html>"""

def _otp_block(otp: str) -> str:
    """Display the code large, centered, and easy to read."""
    return (
        '<p style="margin:24px 0;text-align:center;font-size:32px;font-weight:bold;'
        'letter-spacing:8px;font-family:Courier New,monospace;color:#111827;">'
        f"{escape(otp)}</p>"
    )

# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


def build_verification_otp_email(name: str, otp: str) -> EmailContent:
    """Build the email sent after sign-up to verify the user's email address."""
    minutes = settings.otp_expire_minutes
    safe_name = escape(name)  # the name comes from user input: always escape it in HTML

    subject = f"{settings.app_name}: verify your email"

    text_body = (
        f"Hi {name},\n\n"
        f"Thanks for signing up for {settings.app_name}. "
        "Use this code to verify your email address:\n\n"
        f"    {otp}\n\n"
        f"This code expires in {minutes} minutes and can only be used once.\n\n"
        "If you didn't create an account, you can safely ignore this email.\n"
    )

    content_html = f"""
      <p style="margin:0 0 12px;font-size:15px;line-height:1.5;">Hi {safe_name},</p>
      <p style="margin:0;font-size:15px;line-height:1.5;">
        Thanks for signing up. Use this code to verify your email address:
      </p>
      {_otp_block(otp)}
      <p style="margin:0 0 12px;font-size:14px;line-height:1.5;">
        This code expires in <strong>{minutes} minutes</strong> and can only be used once.
      </p>
      <p style="margin:0;font-size:14px;line-height:1.5;color:#6b7280;">
        If you didn't create an account, you can safely ignore this email.
      </p>
    """

    return EmailContent(
        subject=subject,
        text_body=text_body,
        html_body=_html_layout("Verify your email", content_html),
    )

# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


def build_password_reset_otp_email(name: str, otp: str) -> EmailContent:
    """Build the email sent when a user requests a password reset."""
    minutes = settings.otp_expire_minutes
    safe_name = escape(name)

    subject = f"{settings.app_name}: reset your password"

    text_body = (
        f"Hi {name},\n\n"
        "We received a request to reset your password. "
        "Use this code to choose a new password:\n\n"
        f"    {otp}\n\n"
        f"This code expires in {minutes} minutes and can only be used once.\n\n"
        "Never share this code with anyone. We will never ask you for it.\n\n"
        "If you didn't request a password reset, you can safely ignore this email. "
        "Your password will not change.\n"
    )

    content_html = f"""
      <p style="margin:0 0 12px;font-size:15px;line-height:1.5;">Hi {safe_name},</p>
      <p style="margin:0;font-size:15px;line-height:1.5;">
        We received a request to reset your password. Use this code to choose a new password:
      </p>
      {_otp_block(otp)}
      <p style="margin:0 0 12px;font-size:14px;line-height:1.5;">
        This code expires in <strong>{minutes} minutes</strong> and can only be used once.
      </p>
      <p style="margin:0 0 12px;font-size:14px;line-height:1.5;">
        <strong>Never share this code with anyone.</strong> We will never ask you for it.
      </p>
      <p style="margin:0;font-size:14px;line-height:1.5;color:#6b7280;">
        If you didn't request a password reset, you can safely ignore this email.
        Your password will not change.
      </p>
    """

    return EmailContent(
        subject=subject,
        text_body=text_body,
        html_body=_html_layout("Reset your password", content_html),
    )