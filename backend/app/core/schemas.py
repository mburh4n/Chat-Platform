from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    """A simple confirmation, e.g. {"message": "Email verified successfully."}"""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"message": "Operation completed successfully."}]}
    )

    message: str


class ErrorResponse(BaseModel):
    """The shape FastAPI uses for errors raised with HTTPException.

    Used to document error responses in Swagger.
    Note: validation errors (422) use a list in "detail" instead of a string.
    """

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"detail": "A description of what went wrong."}]}
    )

    detail: str
