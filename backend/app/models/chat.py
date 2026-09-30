from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document


class ChatMessage(Base):
    """One question about a document and the answer it received."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        # History is always loaded per document, in time order
        Index("ix_chat_messages_document_created", "document_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Owner, stored directly so every history query can filter by user
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE")
    )

    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)

    # True when the answer used the MCP word-definition tool
    used_tool: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} document_id={self.document_id} used_tool={self.used_tool}>"
