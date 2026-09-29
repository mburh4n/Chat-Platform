import logging
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings
from app.emails.templates import (
    build_password_reset_otp_email,
    build_verification_otp_email,
)

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised when an email could not be sent."""


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """Send an email through Gmail SMTP (STARTTLS on port 587).

    Always includes a plain-text body; the HTML body is optional.
    Raises EmailSendError if anything goes wrong.
    """
    # 1. Build the message
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = to_email
    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    # 2. Secure settings that also verify Gmail's certificate
    context = ssl.create_default_context()

    # 3. Connect, encrypt, log in, send, disconnect
    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as server:
            server.starttls(context=context)
            server.login(
                settings.smtp_username,
                settings.smtp_password.get_secret_value(),
            )
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        # Never log the password or the email contents
        logger.error("Failed to send email to %s: %s", to_email, exc)
        raise EmailSendError("Could not send email") from exc

    logger.info("Email sent to %s", to_email)

    # ---------------------------------------------------------------------------
# OTP emails (used by the auth endpoints, usually as background tasks)
# ---------------------------------------------------------------------------


def send_verification_otp_email(to_email: str, name: str, otp: str) -> None:
    """Send the sign-up email verification code."""
    content = build_verification_otp_email(name=name, otp=otp)
    send_email(
        to_email=to_email,
        subject=content.subject,
        text_body=content.text_body,
        html_body=content.html_body,
    )

def send_password_reset_otp_email(to_email: str, name: str, otp: str) -> None:
    """Send the password reset code."""
    content = build_password_reset_otp_email(name=name, otp=otp)
    send_email(
        to_email=to_email,
        subject=content.subject,
        text_body=content.text_body,
        html_body=content.html_body,
    )


# ---------------------------------------------------------------------------
# Background sending
# ---------------------------------------------------------------------------


def safe_send(send_function: Callable[..., None], **kwargs: object) -> None:
    """Run an email function as a background task without crashing.

    Failures are already logged inside send_email, so they are only
    swallowed here. The user can request a new code if an email never arrives.
    """
    try:
        send_function(**kwargs)
    except EmailSendError:
        pass
