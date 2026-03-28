"""Custom exceptions for the PyWuzzuf client."""

from __future__ import annotations


class WuzzufAPIError(Exception):
    """
    Base exception for all Wuzzuf API related errors.

    Parameters
    ----------
    message : str
        The error message.
    status_code : int, optional
        The HTTP status code returned by the API, if available.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(f"[HTTP {status_code}] {message}" if status_code else message)


class RateLimitError(WuzzufAPIError):
    """
    Raised when the API rate limit is exceeded (HTTP 429).

    The client automatically retries on this error with exponential back-off
    before eventually propagating it if the limit persists.
    """


class InvalidResponseError(WuzzufAPIError):
    """
    Raised when the API response fails Pydantic validation.

    This usually indicates that the API schema has changed or returned
    unexpected data structures.

    Parameters
    ----------
    message : str
        The error message.
    validation_error : Exception, optional
        The underlying Pydantic validation error.
    status_code : int, optional
        The HTTP status code.
    """

    def __init__(
        self,
        message: str,
        *,
        validation_error: Exception | None = None,
        status_code: int | None = None,
    ) -> None:
        self.validation_error = validation_error
        detail = f"{message} — Details: {validation_error}" if validation_error else message
        super().__init__(detail, status_code=status_code)


class BotDetectionError(WuzzufAPIError):
    """
    Raised when repeated 403 responses suggest bot-detection rejection.

    This error is raised by ``HttpCore`` after 3 consecutive HTTP 403
    responses. The recommended first step is to update the ``impersonate``
    parameter on the client to a more recent browser string.
    """
