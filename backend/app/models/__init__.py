# Import every model in this file so that Alembic can find all tables.
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.otp import EmailOTP, PasswordResetOTP
from app.models.user import User

__all__ = ["User", "EmailOTP", "PasswordResetOTP", "Document", "DocumentChunk", "DocumentStatus"]
