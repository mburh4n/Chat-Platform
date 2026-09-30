from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.chat import ChatMessage
    from app.models.user import User

# gemini-embedding-001 with output_dimensionality=768.
# Changing this needs a migration AND re-embedding every chunk.
EMBEDDING_DIMENSION = 768


class DocumentStatus(StrEnum):
    PROCESSING = "processing"  # uploaded, text is being extracted and embedded
    READY = "ready"  # chunks and embeddings stored: can be chatted with
    FAILED = "failed"  # see error_message


class Document(Base):
    """An uploaded PDF. The file itself lives on disk under stored_filename."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Owner. Deleting the user deletes their documents.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # The name the user uploaded (shown in the UI, never used as a path)
    original_filename: Mapped[str] = mapped_column(String(255))

    # Random unique name on disk, so users can't overwrite or guess each other's files
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)

    file_size: Mapped[int] = mapped_column(Integer)  # bytes
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0")
    )

    # Stored as VARCHAR with a CHECK constraint (portable, easy to extend)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=DocumentStatus.PROCESSING,
        server_default=DocumentStatus.PROCESSING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="documents")

    # Deleting a document deletes its chunks and chat messages
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} user_id={self.user_id} status={self.status}>"


class DocumentChunk(Base):
    """A piece of a document's text with its embedding vector."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
        # HNSW = approximate nearest-neighbour index; vector_cosine_ops matches
        # the <=> (cosine distance) operator used by vector search
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    # Stored on the chunk too, so every search can filter by owner directly
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer)  # 0, 1, 2... order in the document
    page_number: Mapped[int] = mapped_column(Integer)  # 1-based page the text came from
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk id={self.id} document_id={self.document_id} "
            f"index={self.chunk_index} page={self.page_number}>"
        )
