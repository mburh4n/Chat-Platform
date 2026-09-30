"""Application errors that the global exception handler turns into JSON responses.

Services raise these instead of HTTPException, so business logic
stays independent of HTTP. Every error is sent as {"detail": "..."}.
"""


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class TooManyRequestsError(AppError):
    status_code = 429


class PayloadTooLargeError(AppError):
    status_code = 413


class ServiceUnavailableError(AppError):
    """An outside service we depend on (Gemini, the MCP server) failed."""

    status_code = 503
