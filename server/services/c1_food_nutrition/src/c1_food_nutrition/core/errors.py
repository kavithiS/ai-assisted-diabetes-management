"""Domain errors and the stable machine-readable error codes exposed by the API.

Errors here carry no HTTP knowledge; ``api/exception_handlers.py`` maps codes to statuses.
"""

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    """Stable error codes returned in ``error.code`` (ADR 0004)."""

    IMAGE_REQUIRED = "IMAGE_REQUIRED"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    IMAGE_UNREADABLE = "IMAGE_UNREADABLE"
    INVALID_METADATA = "INVALID_METADATA"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class ErrorDetailItem:
    """One field-level problem attached to an error."""

    issue: str
    field: str | None = None


class AppError(Exception):
    """Base class for expected, client-facing errors."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str, details: list[ErrorDetailItem] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: list[ErrorDetailItem] = details or []


class ImageRequiredError(AppError):
    """No image was uploaded, or the uploaded file is empty."""

    code = ErrorCode.IMAGE_REQUIRED


class UnsupportedMediaTypeError(AppError):
    """The request or image is not of a supported type."""

    code = ErrorCode.UNSUPPORTED_MEDIA_TYPE


class ImageTooLargeError(AppError):
    """The uploaded image exceeds ``MAX_IMAGE_BYTES``."""

    code = ErrorCode.IMAGE_TOO_LARGE


class ImageUnreadableError(AppError):
    """The bytes look like a supported format but cannot be decoded (corrupt/truncated)."""

    code = ErrorCode.IMAGE_UNREADABLE


class InvalidMetadataError(AppError):
    """One or more metadata form fields are invalid."""

    code = ErrorCode.INVALID_METADATA


class NotFoundError(AppError):
    """The requested resource does not exist."""

    code = ErrorCode.NOT_FOUND


class InvalidRequestError(AppError):
    """The request is well-formed but a value in it is not acceptable."""

    code = ErrorCode.VALIDATION_ERROR
