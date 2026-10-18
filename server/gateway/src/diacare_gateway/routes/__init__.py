"""Gateway routes. Each module proxies one path prefix to one service."""

import uuid

import httpx
from fastapi import Request, Response

from diacare_gateway.config import GatewaySettings
from diacare_shared.errors import AppError, ErrorCode
from diacare_shared.internal_auth import INTERNAL_TOKEN_HEADER, PATIENT_ID_HEADER
from diacare_shared.request_context import REQUEST_ID_HEADER, get_request_id

PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

# Headers that must not be copied between the client and the upstream service.
_EXCLUDED_HEADERS = {
    "connection",
    "content-encoding",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
# Sent by the client but never trusted: the gateway sets its own (ADR 0005).
_CLIENT_IDENTITY_HEADERS = {
    "authorization",
    PATIENT_ID_HEADER.lower(),
    INTERNAL_TOKEN_HEADER.lower(),
    REQUEST_ID_HEADER.lower(),
}
# The gateway adds its own date, server and request id.
_SKIPPED_RESPONSE_HEADERS = _EXCLUDED_HEADERS | {"date", "server", REQUEST_ID_HEADER.lower()}


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """The shared HTTP client for calls to the services (created at startup)."""
    client: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if client is None:
        raise RuntimeError("The HTTP client is not initialised: the app lifespan did not run.")
    return client


async def forward(
    request: Request,
    client: httpx.AsyncClient,
    base_url: str,
    upstream_path: str,
    *,
    patient_id: uuid.UUID,
    settings: GatewaySettings,
    timeout: float | None = None,
) -> Response:
    """Forward the request to `base_url + upstream_path` as `patient_id` and relay the answer."""
    url = f"{base_url.rstrip('/')}/{upstream_path.lstrip('/')}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _EXCLUDED_HEADERS and k.lower() not in _CLIENT_IDENTITY_HEADERS
    }
    headers[PATIENT_ID_HEADER] = str(patient_id)
    if settings.internal_token:
        headers[INTERNAL_TOKEN_HEADER] = settings.internal_token
    request_id = get_request_id()
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id

    try:
        upstream = await client.request(
            request.method,
            url,
            params=request.query_params,
            headers=headers,
            content=await request.body(),
            timeout=timeout if timeout is not None else settings.default_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise AppError(
            504, ErrorCode.UPSTREAM_TIMEOUT, "The service took too long to answer."
        ) from exc
    except httpx.RequestError as exc:
        raise AppError(502, ErrorCode.UPSTREAM_UNAVAILABLE, "The service is unavailable.") from exc

    response_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _SKIPPED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
