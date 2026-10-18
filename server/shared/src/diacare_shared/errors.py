"""The error envelope every server package returns (same shape as C1, ADR 0004).

{"error": {"code": "...", "message": "...", "details": [{"field": "...", "issue": "..."}]},
 "request_id": "..."}
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from diacare_shared.request_context import get_request_id


class ErrorCode(StrEnum):
    """Codes shared by the gateway and the services. A package may add its own string codes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    TOO_MANY_ATTEMPTS = "TOO_MANY_ATTEMPTS"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_CODE_BY_STATUS: Mapping[int, ErrorCode] = {
    400: ErrorCode.MALFORMED_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.PAYLOAD_TOO_LARGE,
    429: ErrorCode.TOO_MANY_ATTEMPTS,
    501: ErrorCode.NOT_IMPLEMENTED,
    502: ErrorCode.UPSTREAM_UNAVAILABLE,
    503: ErrorCode.SERVICE_UNAVAILABLE,
    504: ErrorCode.UPSTREAM_TIMEOUT,
}


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    """One field-level problem attached to an error."""

    issue: str
    field: str | None = None


class AppError(Exception):
    """An expected, client-facing error. Raise it anywhere; the handler builds the response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: Sequence[ErrorDetail] = (),
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = str(code)
        self.message = message
        self.details = list(details)
        self.headers = dict(headers) if headers else None


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Sequence[ErrorDetail] = (),
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """A JSON response in the standard envelope."""
    body: dict[str, Any] = {
        "error": {
            "code": str(code),
            "message": message,
            "details": [{"field": d.field, "issue": d.issue} for d in details],
        },
        "request_id": get_request_id(),
    }
    return JSONResponse(
        status_code=status_code, content=body, headers=dict(headers) if headers else None
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101 - narrowed by registration
    return error_response(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


async def _validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    details = [
        ErrorDetail(
            field=".".join(str(p) for p in e["loc"][1:]) or None, issue=str(e.get("msg", ""))
        )
        for e in exc.errors()
    ]
    return error_response(
        422, ErrorCode.VALIDATION_ERROR, "The request is invalid.", details=details
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = _CODE_BY_STATUS.get(
        exc.status_code,
        ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else ErrorCode.HTTP_ERROR,
    )
    message = exc.detail if isinstance(exc.detail, str) else str(code)
    return error_response(exc.status_code, code, message, headers=exc.headers)


def install_exception_handlers(app: FastAPI) -> None:
    """Make ``app`` answer every error with the standard envelope."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
