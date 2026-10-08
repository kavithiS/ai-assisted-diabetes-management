"""Gateway routes. Each module proxies one path prefix to one service."""

from collections.abc import AsyncIterator

import httpx
from fastapi import HTTPException, Request, Response

from diacare_gateway.config import get_settings

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


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Yield an HTTP client for calls to the services."""
    async with httpx.AsyncClient(timeout=get_settings().request_timeout_seconds) as client:
        yield client


async def forward(
    request: Request, client: httpx.AsyncClient, base_url: str, upstream_path: str
) -> Response:
    """Forward the incoming request to `base_url + upstream_path` and relay the response."""
    url = f"{base_url.rstrip('/')}/{upstream_path.lstrip('/')}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _EXCLUDED_HEADERS}
    try:
        upstream = await client.request(
            request.method,
            url,
            params=request.query_params,
            headers=headers,
            content=await request.body(),
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Upstream service unavailable") from exc

    response_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _EXCLUDED_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
