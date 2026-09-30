"""Turn text into embedding vectors with Gemini.

An embedding is a list of numbers that captures the MEANING of a text.
Texts with similar meaning get vectors pointing in similar directions,
which is what vector search measures (cosine distance).
"""

import logging
import math
import time

from google.genai import errors, types

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.llm.client import get_gemini_client
from app.models.document import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)

# Texts sent to Gemini per request (the API accepts up to 100)
BATCH_SIZE = 100

# Temporary failures worth retrying: rate limit, server errors
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3


class EmbeddingError(Exception):
    """Embeddings could not be created."""


def _normalize(vector: list[float]) -> list[float]:
    """Scale a vector to length 1.

    Gemini only returns unit-length vectors at the full 3072 dimensions; at 768
    they must be normalized by us so that all vectors are comparable.
    """
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0:
        return vector
    return [value / length for value in vector]


def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    client = get_gemini_client()
    config = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=EMBEDDING_DIMENSION,
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=texts,
                config=config,
            )
            break
        except errors.APIError as exc:
            retryable = exc.code in RETRYABLE_STATUS_CODES
            if not retryable or attempt == MAX_ATTEMPTS:
                logger.error("Embedding request failed (%s): %s", exc.code, exc.message)
                raise EmbeddingError("The embedding service returned an error.") from exc
            wait_seconds = 2**attempt  # 2s, 4s
            logger.warning("Embedding request failed (%s), retrying in %ss", exc.code, wait_seconds)
            time.sleep(wait_seconds)

    vectors = [embedding.values for embedding in response.embeddings or []]
    if len(vectors) != len(texts):
        raise EmbeddingError("The embedding service returned an unexpected number of vectors.")
    return [_normalize(list(vector)) for vector in vectors]


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed document chunks, in batches. Returns one vector per text, same order."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        vectors.extend(_embed_batch(texts[start : start + BATCH_SIZE], "RETRIEVAL_DOCUMENT"))
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a user's question.

    RETRIEVAL_QUERY is tuned to match RETRIEVAL_DOCUMENT vectors of passages
    that answer the question. Raises ServiceUnavailableError (503) on failure.
    """
    try:
        return _embed_batch([text], "RETRIEVAL_QUERY")[0]
    except EmbeddingError as exc:
        raise ServiceUnavailableError(
            "Could not process your question right now. Please try again."
        ) from exc
