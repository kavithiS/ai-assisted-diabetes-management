"""Proxy `/api/v1/foot/*` to C4 (c4_foot_monitoring)."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response

from diacare_gateway.config import GatewaySettings, get_settings
from diacare_gateway.routes import PROXY_METHODS, forward, get_http_client

router = APIRouter(prefix="/api/v1/foot", tags=["foot (C4)"])


@router.api_route("/{path:path}", methods=PROXY_METHODS)
async def proxy_foot(
    path: str,
    request: Request,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[GatewaySettings, Depends(get_settings)],
) -> Response:
    return await forward(request, client, settings.c4_url, f"/v1/foot/{path}")
