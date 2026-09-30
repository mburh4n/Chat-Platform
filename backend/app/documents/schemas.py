from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    """An uploaded PDF as shown to its owner. The stored filename stays private."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "original_filename": "handbook.pdf",
                    "file_size": 482133,
                    "page_count": 12,
                    "chunk_count": 37,
                    "status": "ready",
                    "error_message": None,
                    "created_at": "2026-09-30T10:15:02Z",
                }
            ]
        },
    )

    id: int
    original_filename: str
    file_size: int
    page_count: int | None
    chunk_count: int
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
