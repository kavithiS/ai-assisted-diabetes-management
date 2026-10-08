"""Proxy `/api/v1/risk/*` to C3 (c3_risk_xai)."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response

from diacare_gateway.config import GatewaySettings, get_settings
from diacare_gateway.routes import PROXY_METHODS, forward, get_http_client

router = APIRouter(prefix="/api/v1/risk", tags=["risk (C3)"])


@router.api_route("/{path:path}", methods=PROXY_METHODS)
async def proxy_risk(
    path: str,
    request: Request,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[GatewaySettings, Depends(get_settings)],
) -> Response:
    return await forward(request, client, settings.c3_url, f"/v1/risk/{path}")
