"""Proxy `/api/v1/glucose/*` to C2 (c2_glycemic_forecasting)."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request, Response

from diacare_gateway.auth.deps import PatientId
from diacare_gateway.config import GatewaySettings, get_settings
from diacare_gateway.routes import PROXY_METHODS, forward, get_http_client

router = APIRouter(prefix="/api/v1/glucose", tags=["glucose (C2)"])


@router.api_route("", methods=PROXY_METHODS)
@router.api_route("/{path:path}", methods=PROXY_METHODS)
async def proxy_glucose(
    request: Request,
    patient_id: PatientId,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[GatewaySettings, Depends(get_settings)],
    path: str = "",
) -> Response:
    upstream = f"/v1/glucose/{path}" if path else "/v1/glucose"
    return await forward(
        request, client, settings.c2_url, upstream, patient_id=patient_id, settings=settings
    )
