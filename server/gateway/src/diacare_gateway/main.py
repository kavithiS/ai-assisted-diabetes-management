"""DiaCare AI API gateway (port 8000).

The client talks only to the gateway. The gateway proxies `/api/v1/{meals,glucose,risk,foot}/*`
to C1–C4 and reports the health of every service.
"""

import asyncio
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from diacare_gateway.config import GatewaySettings, get_settings
from diacare_gateway.routes import foot, get_http_client, glucose, meals, risk
from diacare_shared.logging import configure_logging

ServiceStatus = Literal["ok", "error", "unreachable"]


class GatewayHealth(BaseModel):
    status: Literal["ok", "degraded"]
    service: str = "diacare_gateway"
    services: dict[str, ServiceStatus]


configure_logging(get_settings().log_level)

app = FastAPI(title="DiaCare AI Gateway", version="0.1.0")
app.include_router(meals.router)
app.include_router(glucose.router)
app.include_router(risk.router)
app.include_router(foot.router)


async def _check(client: httpx.AsyncClient, url: str, timeout: float) -> ServiceStatus:
    try:
        response = await client.get(f"{url.rstrip('/')}/health", timeout=timeout)
    except httpx.RequestError:
        return "unreachable"
    if response.status_code == 200 and response.json().get("status") == "ok":
        return "ok"
    return "error"


@app.get("/health", response_model=GatewayHealth)
async def health(
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
    settings: Annotated[GatewaySettings, Depends(get_settings)],
) -> GatewayHealth:
    urls = settings.service_urls()
    results = await asyncio.gather(
        *(_check(client, url, settings.health_timeout_seconds) for url in urls.values())
    )
    services = dict(zip(urls, results, strict=True))
    overall: Literal["ok", "degraded"] = (
        "ok" if all(s == "ok" for s in services.values()) else "degraded"
    )
    return GatewayHealth(status=overall, services=services)
