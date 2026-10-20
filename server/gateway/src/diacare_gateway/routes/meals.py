"""Proxy `/api/v1/meals/*` to C1 (c1_food_nutrition)."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response

from diacare_gateway.auth.deps import PatientId
from diacare_gateway.config import GatewaySettings, get_settings
from diacare_gateway.routes import PROXY_METHODS, forward, get_http_client

router = APIRouter(prefix="/api/v1/meals", tags=["meals (C1)"])


@router.api_route("", methods=PROXY_METHODS)
@router.api_route("/{path:path}", methods=PROXY_METHODS)
async def proxy_meals(
    request: Request,
    patient_id: PatientId,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[GatewaySettings, Depends(get_settings)],
    path: str = "",
) -> Response:
    upstream = f"/v1/meals/{path}" if path else "/v1/meals"
    # Photo analysis is the one slow call; everything else gets the short timeout.
    timeout = settings.request_timeout_seconds if path == "analyze" else None
    return await forward(
        request,
        client,
        settings.c1_url,
        upstream,
        patient_id=patient_id,
        settings=settings,
        timeout=timeout,
    )
