from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class AskQuestionRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"question": "What is the main topic of this document?"}]},
    )

    question: Question


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "document_id": 3,
                    "question": "What does authentication mean?",
                    "answer": "Authentication is the process of verifying who someone is...",
                    "used_tool": True,
                    "created_at": "2026-09-30T10:15:02Z",
                }
            ]
        },
    )

    id: int
    document_id: int
    question: str
    answer: str
    used_tool: bool
    created_at: datetime
