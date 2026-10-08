"""ASGI middleware: request correlation/logging and request-body size limiting."""

import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from c1_food_nutrition.api.exception_handlers import build_error_response
from c1_food_nutrition.core.context import request_id_var
from c1_food_nutrition.core.errors import ErrorCode

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware:
    """Assign a request ID, log one line per request and catch unhandled errors.

    An incoming ``X-Request-ID`` is reused if it is safe; otherwise a new one is
    generated. The ID is echoed in the response header and in error bodies.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process one ASGI connection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = incoming if incoming and _VALID_REQUEST_ID.match(incoming) else uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception("unhandled error")
            if response_started:
                raise
            response = build_error_response(
                500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."
            )
            await response(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request completed",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_var.reset(token)


class RequestBodyTooLargeError(StarletteHTTPException):
    """Raised from ``receive`` when a streamed body exceeds the cap.

    It subclasses Starlette's HTTPException so that FastAPI re-raises it unchanged
    while parsing the body instead of converting it into a generic 400.
    """

    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            status_code=413,
            detail=f"Request body exceeds the maximum allowed size of {max_bytes} bytes.",
        )


class BodySizeLimitMiddleware:
    """Cap the request body size before multipart parsing writes it anywhere.

    Requests with a ``Content-Length`` above the cap are rejected immediately; bodies
    without one (chunked transfer) are counted while streaming and aborted once
    they exceed it. The exact per-image limit is enforced again by ``ImageValidator``.
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process one ASGI connection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        declared_length = (
            int(content_length) if content_length and content_length.isdigit() else None
        )
        if declared_length is not None and declared_length > self.max_body_bytes:
            response = build_error_response(
                413,
                ErrorCode.IMAGE_TOO_LARGE,
                f"Request body exceeds the maximum allowed size of {self.max_body_bytes} bytes.",
            )
            await response(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise RequestBodyTooLargeError(self.max_body_bytes)
            return message

        await self.app(scope, limited_receive, send)
