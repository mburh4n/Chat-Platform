"""Find the chunks of ONE document that are most similar to a question."""

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import DocumentChunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_index: int
    page_number: int
    content: str
    distance: float  # cosine distance: 0 = same meaning, 2 = opposite


def search_chunks(
    db: Session,
    *,
    user_id: int,
    document_id: int,
    query_embedding: list[float],
    top_k: int,
) -> list[RetrievedChunk]:
    """Return the top_k chunks closest to the query, nearest first.

    Both user_id AND document_id are filtered, so a search can never reach
    another user's data or another document, even if a document id is guessed.
    """
    # The HNSW index finds nearest neighbours first and filters afterwards.
    # With filters, a plain scan could return fewer than top_k rows; an
    # iterative scan keeps searching until enough matching rows are found.
    # SET LOCAL only lasts until the end of the current transaction.
    db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))

    # <=> is pgvector's cosine distance operator
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
    rows = db.execute(
        select(DocumentChunk.chunk_index, DocumentChunk.page_number, DocumentChunk.content, distance)
        .where(DocumentChunk.user_id == user_id, DocumentChunk.document_id == document_id)
        .order_by(distance)
        .limit(top_k)
    ).all()

    return [
        RetrievedChunk(
            chunk_index=row.chunk_index,
            page_number=row.page_number,
            content=row.content,
            distance=float(row.distance),
        )
        for row in rows
    ]
