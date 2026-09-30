from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.chat import service as chat_service
from app.chat.schemas import AskQuestionRequest, ChatMessageResponse
from app.core.database import get_db
from app.core.schemas import ErrorResponse
from app.models import ChatMessage, User

router = APIRouter(
    prefix="/api/documents/{document_id}",
    tags=["Chat"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)


@router.post(
    "/chat",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Document is not ready"},
        503: {"model": ErrorResponse, "description": "The AI service is unavailable"},
    },
)
def ask_question(
    document_id: int,
    payload: AskQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessage:
    """Ask a question about one of your documents. The question and answer are saved."""
    return chat_service.ask_question(db, current_user, document_id, payload)


@router.get("/messages", response_model=list[ChatMessageResponse])
def list_messages(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatMessage]:
    """Previous questions and answers for a document, oldest first."""
    return chat_service.list_messages(db, current_user, document_id)
