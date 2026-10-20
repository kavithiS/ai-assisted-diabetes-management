"""C4 error codes and the error envelope.

Same shape as C1 and the planned ``diacare_shared.errors`` (on C1's branch, not yet in
``main``)::

    {"error": {"code": "...", "message": "...", "details": [{"field": "...", "issue": "..."}]},
     "request_id": "..."}

Switch to ``diacare_shared.errors`` once it is merged into ``main``.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class ErrorCode(StrEnum):
    """Error codes returned by C4."""

    IMAGE_REQUIRED = "IMAGE_REQUIRED"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    IMAGE_UNREADABLE = "IMAGE_UNREADABLE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
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
    """An expected, client-facing error. The handler turns it into the envelope."""

    status_code: int = 500
    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str, details: list[ErrorDetailItem] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class ImageRequiredError(AppError):
    status_code = 422
    code = ErrorCode.IMAGE_REQUIRED


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = ErrorCode.UNSUPPORTED_MEDIA_TYPE


class ImageTooLargeError(AppError):
    status_code = 413
    code = ErrorCode.IMAGE_TOO_LARGE


class ImageUnreadableError(AppError):
    status_code = 422
    code = ErrorCode.IMAGE_UNREADABLE


_CODE_BY_STATUS: dict[int, ErrorCode] = {
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
}


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetailItem] | None = None,
) -> JSONResponse:
    """A JSON response in the standard envelope."""
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "details": [{"field": d.field, "issue": d.issue} for d in details or []],
        },
        "request_id": request.headers.get(REQUEST_ID_HEADER),
    }
    return JSONResponse(status_code=status_code, content=body)


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - narrowed by registration
    return error_response(request, exc.status_code, exc.code, exc.message, exc.details)


def _is_missing_image(error: dict[str, Any]) -> bool:
    loc = error.get("loc", ())
    return error.get("type") == "missing" and len(loc) > 0 and loc[-1] == "image"


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = list(exc.errors())
    if any(_is_missing_image(e) for e in errors):
        return error_response(
            request,
            422,
            ErrorCode.IMAGE_REQUIRED,
            "A foot image is required.",
            [ErrorDetailItem(field="image", issue="missing")],
        )
    details = [
        ErrorDetailItem(
            field=".".join(str(part) for part in e.get("loc", ())) or None,
            issue=str(e.get("msg", "invalid")),
        )
        for e in errors
    ]
    return error_response(
        request, 422, ErrorCode.VALIDATION_ERROR, "The request is not valid.", details
    )


async def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = _CODE_BY_STATUS.get(exc.status_code, ErrorCode.HTTP_ERROR)
    return error_response(request, exc.status_code, code, str(exc.detail))


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return error_response(
        request, 500, ErrorCode.INTERNAL_ERROR, "Something went wrong. Please try again."
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Return every error in the envelope."""
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
