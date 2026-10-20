"""Map domain and framework errors to the single ``ErrorResponse`` envelope (ADR 0004)."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from c1_food_nutrition.core.context import get_request_id
from c1_food_nutrition.core.errors import AppError, ErrorCode
from c1_food_nutrition.schemas.common import ErrorBody, ErrorDetail, ErrorResponse
from diacare_shared.errors import AppError as SharedAppError
from diacare_shared.errors import app_error_handler as shared_app_error_handler

logger = logging.getLogger(__name__)

STATUS_BY_CODE: Mapping[ErrorCode, int] = {
    ErrorCode.IMAGE_REQUIRED: 422,
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: 415,
    ErrorCode.IMAGE_TOO_LARGE: 413,
    ErrorCode.IMAGE_UNREADABLE: 422,
    ErrorCode.INVALID_METADATA: 422,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.MALFORMED_REQUEST: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.HTTP_ERROR: 400,
    ErrorCode.INTERNAL_ERROR: 500,
}

_CODE_BY_HTTP_STATUS: Mapping[int, ErrorCode] = {
    400: ErrorCode.MALFORMED_REQUEST,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.IMAGE_TOO_LARGE,
    415: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
}

#: Name of the upload field of /meals/analyze; validation errors on it mean "no image".
_IMAGE_FIELD = "image"

#: Form-field errors on this path are metadata problems; JSON-body errors elsewhere are not.
_ANALYZE_PATH = "/meals/analyze"


def build_error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: Sequence[ErrorDetail] = (),
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Create a JSON response in the standard error envelope."""
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=list(details)),
        request_id=get_request_id(),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=dict(headers) if headers else None,
    )


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle expected domain errors raised by services and dependencies."""
    assert isinstance(exc, AppError)  # noqa: S101 - narrowed by registration below
    status_code = STATUS_BY_CODE[exc.code]
    logger.info(
        "request rejected",
        extra={"error_code": exc.code.value, "status_code": status_code, "path": request.url.path},
    )
    details = [ErrorDetail(field=d.field, issue=d.issue) for d in exc.details]
    return build_error_response(status_code, exc.code, exc.message, details)


def _field_name(error: Mapping[str, Any]) -> str | None:
    loc = error.get("loc", ())
    return str(loc[-1]) if len(loc) > 1 else None


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert FastAPI request validation errors into the error envelope."""
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = list(exc.errors())
    details = [ErrorDetail(field=_field_name(e), issue=str(e.get("msg", ""))) for e in errors]

    if any(_field_name(e) == _IMAGE_FIELD for e in errors):
        code, message = ErrorCode.IMAGE_REQUIRED, "An image file is required in the 'image' field."
    elif (
        errors
        and request.url.path.endswith(_ANALYZE_PATH)
        and all(e.get("loc", ("",))[0] == "body" for e in errors)
    ):
        code, message = ErrorCode.INVALID_METADATA, "One or more form fields are invalid."
    else:
        code, message = ErrorCode.VALIDATION_ERROR, "The request is invalid."

    logger.info(
        "request rejected",
        extra={"error_code": code.value, "status_code": 422, "path": request.url.path},
    )
    return build_error_response(STATUS_BY_CODE[code], code, message, details)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Wrap framework HTTP errors (404, 405, body parsing, ...) in the error envelope."""
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = _CODE_BY_HTTP_STATUS.get(
        exc.status_code,
        ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else ErrorCode.HTTP_ERROR,
    )
    message = exc.detail if isinstance(exc.detail, str) else code.value
    return build_error_response(exc.status_code, code, message, headers=exc.headers)


def register_exception_handlers(app: FastAPI) -> None:
    """Install all error handlers on ``app``."""
    app.add_exception_handler(AppError, app_error_handler)
    # Errors raised by shared helpers (for example the internal-token check).
    app.add_exception_handler(SharedAppError, shared_app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
