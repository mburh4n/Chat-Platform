import logging
import sys

from app.core.config import settings
from app.emails.service import EmailSendError, send_email

# Show log messages in the terminal
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# Send to the address given on the command line, or to yourself by default
recipient = sys.argv[1] if len(sys.argv) > 1 else settings.smtp_username

text_body = (
    "Hello!\n\n"
    "This is a test email from the PDF Chat Platform backend.\n"
    "If you can read this, Gmail SMTP is working.\n"
)

html_body = """
<html>
  <body style="font-family: Arial, sans-serif;">
    <h2>Hello!</h2>
    <p>This is a test email from the <strong>PDF Chat Platform</strong> backend.</p>
    <p>If you can read this, Gmail SMTP is working. &#9989;</p>
  </body>
</html>
"""

print(f"Sending a test email to {recipient} ...")

try:
    send_email(
        to_email=recipient,
        subject="PDF Chat Platform: SMTP test",
        text_body=text_body,
        html_body=html_body,
    )
except EmailSendError as exc:
    print("FAILED:", exc)
    print("Original error:", repr(exc.__cause__))
    sys.exit(1)

print("Success! Check the inbox (and the spam folder).")