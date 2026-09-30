from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.schemas import AskQuestionRequest
from app.core.config import settings
from app.core.exceptions import ConflictError
from app.documents.service import get_user_document
from app.embeddings.service import embed_query
from app.llm.service import generate_answer
from app.models import ChatMessage, DocumentStatus, User
from app.vector_search.service import search_chunks


def ask_question(db: Session, user: User, document_id: int, data: AskQuestionRequest) -> ChatMessage:
    """The RAG pipeline: embed question -> vector search -> LLM (+ MCP tools) -> save.

    Raises 404 if the document isn't the user's, 409 if it isn't ready.
    Nothing is saved if embedding or the LLM fails (503).
    """
    document = get_user_document(db, user, document_id)
    if document.status != DocumentStatus.READY:
        raise ConflictError("This document is not ready for questions yet.")

    # 1. Embed the question
    query_embedding = embed_query(data.question)

    # 2. The most similar chunks of THIS document of THIS user
    chunks = search_chunks(
        db,
        user_id=user.id,
        document_id=document.id,
        query_embedding=query_embedding,
        top_k=settings.retrieval_top_k,
    )

    # 3. Answer from those chunks only (the LLM may call the MCP dictionary tool)
    answer = generate_answer(data.question, chunks)

    # 4. Save the question and answer
    message = ChatMessage(
        user_id=user.id,
        document_id=document.id,
        question=data.question,
        answer=answer.text,
        used_tool=answer.used_tool,
    )
    db.add(message)
    db.commit()
    return message


def list_messages(db: Session, user: User, document_id: int) -> list[ChatMessage]:
    """Chat history of one of the user's documents, oldest first."""
    get_user_document(db, user, document_id)  # 404 unless it's the user's
    return list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.user_id == user.id, ChatMessage.document_id == document_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    )
