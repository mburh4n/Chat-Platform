import logging
import os
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import (
    AppError,
    BadRequestError,
    NotFoundError,
    PayloadTooLargeError,
)
from app.documents import storage
from app.documents.processing import (
    NO_TEXT_MESSAGE,
    PDFProcessingError,
    build_chunks,
    extract_pages,
)
from app.embeddings.service import EmbeddingError, embed_documents
from app.models import Document, DocumentChunk, DocumentStatus, User

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}
PDF_MAGIC_BYTES = b"%PDF-"
DOCUMENT_NOT_FOUND_MESSAGE = "Document not found."


@dataclass(frozen=True)
class IncomingFile:
    """What the router hands over for each uploaded file."""

    filename: str | None
    content_type: str | None
    file: BinaryIO


def _clean_filename(filename: str | None) -> str:
    # Keep only the last path part ("C:\\fakepath\\a.pdf" -> "a.pdf") and limit its length
    name = os.path.basename((filename or "").replace("\\", "/")).strip()
    return (name or "document.pdf")[-255:]


def _read_and_validate(incoming: IncomingFile) -> tuple[str, bytes]:
    """Return (display name, bytes) or raise an error that names the file."""
    name = _clean_filename(incoming.filename)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    # 1. Extension
    if not name.lower().endswith(".pdf"):
        raise BadRequestError(f'"{name}" is not a PDF. Only .pdf files can be uploaded.')

    # 2. Content type sent by the browser
    content_type = (incoming.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise BadRequestError(f'"{name}" is not a PDF (content type "{content_type or "unknown"}").')

    # 3. Size: read one byte past the limit, so huge files are never fully loaded
    data = incoming.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise PayloadTooLargeError(
            f'"{name}" is larger than the {settings.max_upload_size_mb} MB limit.'
        )
    if not data:
        raise BadRequestError(f'"{name}" is empty.')

    # 4. Magic bytes: a real PDF starts with "%PDF-", whatever its name says
    if not data.startswith(PDF_MAGIC_BYTES):
        raise BadRequestError(f'"{name}" is not a valid PDF file.')

    return name, data


def create_documents(db: Session, user: User, files: list[IncomingFile]) -> list[Document]:
    """Validate every file, then store them all and create their records.

    All-or-nothing validation: if one file is invalid, nothing is saved.
    Text extraction and embedding happen afterwards in process_document.
    """
    if not files:
        raise BadRequestError("Please choose at least one PDF file.")
    if len(files) > settings.max_files_per_upload:
        raise BadRequestError(
            f"You can upload at most {settings.max_files_per_upload} files at once."
        )

    validated = [_read_and_validate(incoming) for incoming in files]

    saved_filenames: list[str] = []
    try:
        documents = []
        for name, data in validated:
            stored_filename = storage.save_pdf(data)
            saved_filenames.append(stored_filename)
            documents.append(
                Document(
                    user_id=user.id,
                    original_filename=name,
                    stored_filename=stored_filename,
                    file_size=len(data),
                    status=DocumentStatus.PROCESSING,
                )
            )
        db.add_all(documents)
        db.commit()
    except Exception:
        # Don't leave orphan files on disk if the database step failed
        db.rollback()
        for stored_filename in saved_filenames:
            storage.delete_pdf(stored_filename)
        raise

    return documents


def process_document(document_id: int) -> None:
    """Extract, chunk, embed and store one document. Runs as a background task.

    Uses its own database session: the request's session is closed by now.
    Always ends with status "ready" or "failed", never stuck in "processing".
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return  # deleted before processing started

        pages = extract_pages(storage.path_for(document.stored_filename))
        chunks = build_chunks(pages, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise PDFProcessingError(NO_TEXT_MESSAGE)

        vectors = embed_documents([chunk.content for chunk in chunks])

        db.add_all(
            DocumentChunk(
                document_id=document.id,
                user_id=document.user_id,
                chunk_index=index,
                page_number=chunk.page_number,
                content=chunk.content,
                embedding=vector,
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        )
        document.page_count = len(pages)
        document.chunk_count = len(chunks)
        document.status = DocumentStatus.READY
        document.error_message = None
        db.commit()
        logger.info("Document %s ready: %s pages, %s chunks", document.id, len(pages), len(chunks))

    except PDFProcessingError as exc:
        _mark_failed(db, document_id, str(exc))
    except EmbeddingError:
        _mark_failed(db, document_id, "Embeddings could not be created. Please try uploading again later.")
    except AppError as exc:  # e.g. GEMINI_API_KEY missing
        _mark_failed(db, document_id, exc.detail)
    except Exception:
        logger.exception("Unexpected error while processing document %s", document_id)
        _mark_failed(db, document_id, "Something went wrong while processing this PDF.")
    finally:
        db.close()


def _mark_failed(db: Session, document_id: int, message: str) -> None:
    db.rollback()  # discard any half-added chunks
    document = db.get(Document, document_id)
    if document is None:
        return  # deleted while processing: nothing to update
    document.status = DocumentStatus.FAILED
    document.error_message = message
    document.chunk_count = 0
    db.commit()
    logger.info("Document %s failed: %s", document_id, message)


def fail_interrupted_documents(db: Session) -> int:
    """At startup: documents left "processing" by a crash or restart can never finish."""
    result = db.execute(
        update(Document)
        .where(Document.status == DocumentStatus.PROCESSING)
        .values(
            status=DocumentStatus.FAILED,
            error_message="Processing was interrupted. Please delete this file and upload it again.",
        )
    )
    db.commit()
    return result.rowcount


def list_documents(db: Session, user: User) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.user_id == user.id)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
    )


def get_user_document(db: Session, user: User, document_id: int) -> Document:
    """Return the user's document or raise 404.

    Filtering by owner in the query means another user's document is
    indistinguishable from one that doesn't exist (404, never 403).
    """
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise NotFoundError(DOCUMENT_NOT_FOUND_MESSAGE)
    return document


def delete_document(db: Session, user: User, document_id: int) -> None:
    """Delete the record (chunks and chat messages cascade) and then the file."""
    document = get_user_document(db, user, document_id)
    stored_filename = document.stored_filename
    db.delete(document)
    db.commit()
    storage.delete_pdf(stored_filename)  # only after the database change succeeded
