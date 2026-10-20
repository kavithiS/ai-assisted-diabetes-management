"""Request id, one log line per request, and a request-body size cap (ASGI middleware)."""

import logging
import re
import time
from contextvars import ContextVar
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

#: Correlation id of the request being handled, or ``None`` outside a request.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """The current request's correlation id, if any."""
    return request_id_var.get()


class RequestContextMiddleware:
    """Reuse a safe incoming ``X-Request-ID`` (or make one), echo it, and log each request.

    Unhandled errors become a 500 in the standard envelope.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from diacare_shared.errors import ErrorCode, error_response  # avoid an import cycle

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
            response = error_response(
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


class _BodyTooLargeError(StarletteHTTPException):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(
            status_code=413,
            detail=f"Request body exceeds the maximum allowed size of {max_bytes} bytes.",
        )


class BodySizeLimitMiddleware:
    """Reject request bodies over ``max_body_bytes`` (declared, or counted while streaming)."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from diacare_shared.errors import ErrorCode, error_response

        declared = Headers(scope=scope).get("content-length")
        if declared and declared.isdigit() and int(declared) > self.max_body_bytes:
            response = error_response(
                413,
                ErrorCode.PAYLOAD_TOO_LARGE,
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
                    raise _BodyTooLargeError(self.max_body_bytes)
            return message

        await self.app(scope, limited_receive, send)
