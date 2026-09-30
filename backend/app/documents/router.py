from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.schemas import ErrorResponse, MessageResponse
from app.documents import service as documents_service
from app.documents.schemas import DocumentResponse
from app.documents.service import IncomingFile
from app.models import Document, User

router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
    responses={401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"}},
)

NOT_FOUND_RESPONSE = {404: {"model": ErrorResponse, "description": "Document not found"}}


@router.post(
    "",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "A file is not a valid PDF"},
        413: {"model": ErrorResponse, "description": "A file is too large"},
    },
)
def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="One or more PDF files"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Document]:
    """Upload PDFs. They start as "processing"; poll the list until "ready" or "failed"."""
    incoming = [
        IncomingFile(filename=f.filename, content_type=f.content_type, file=f.file) for f in files
    ]
    documents = documents_service.create_documents(db, current_user, incoming)

    # Extraction + embeddings run after the response is sent
    for document in documents:
        background_tasks.add_task(documents_service.process_document, document.id)

    return documents


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Document]:
    """The logged-in user's documents, newest first."""
    return documents_service.list_documents(db, current_user)


@router.get("/{document_id}", response_model=DocumentResponse, responses=NOT_FOUND_RESPONSE)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    return documents_service.get_user_document(db, current_user, document_id)


@router.delete("/{document_id}", response_model=MessageResponse, responses=NOT_FOUND_RESPONSE)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Delete a document, its chunks, its chat history and the stored file."""
    documents_service.delete_document(db, current_user, document_id)
    return MessageResponse(message="Document deleted.")
