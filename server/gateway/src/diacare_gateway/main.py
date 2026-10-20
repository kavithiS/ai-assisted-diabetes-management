"""DiaCare AI API gateway (port 8000).

The client talks only to the gateway. The gateway checks the login, proxies
`/api/v1/{meals,foods,glucose,risk,foot}/*` to C1–C4 on behalf of the signed-in patient, and
reports the health of every service.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from diacare_gateway.auth.rate_limit import LoginRateLimiter
from diacare_gateway.config import GatewaySettings, get_settings
from diacare_gateway.routes import auth, foods, foot, get_http_client, glucose, meals, risk
from diacare_shared.db import make_engine, make_session_factory
from diacare_shared.errors import install_exception_handlers
from diacare_shared.logging import configure_logging
from diacare_shared.request_context import BodySizeLimitMiddleware, RequestContextMiddleware

ServiceStatus = Literal["ok", "error", "unreachable"]


class GatewayHealth(BaseModel):
    status: Literal["ok", "degraded"]
    service: str = "diacare_gateway"
    services: dict[str, ServiceStatus]


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """One HTTP client for all calls to the services, shared by every request."""
    settings: GatewaySettings = app.state.settings
    async with httpx.AsyncClient(
        timeout=settings.default_timeout_seconds,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    ) as client:
        app.state.http_client = client
        yield
    engine = app.state.engine
    if engine is not None:
        engine.dispose()


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    """Build the gateway. Tests pass their own settings."""
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    app = FastAPI(title="DiaCare AI Gateway", version="0.1.0", lifespan=_lifespan)
    app.state.settings = resolved
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: resolved

    # Creating the engine does not connect; the first login request does.
    url = resolved.gateway_database_url
    app.state.engine = make_engine(url, "core") if url else None
    app.state.session_factory = (
        make_session_factory(app.state.engine) if app.state.engine is not None else None
    )
    app.state.rate_limiter = LoginRateLimiter(
        max_failures=resolved.login_max_failures,
        window_seconds=resolved.login_window_minutes * 60,
    )

    install_exception_handlers(app)
    # Middleware added last runs first: RequestContext wraps everything.
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=resolved.max_request_bytes)
    app.add_middleware(RequestContextMiddleware)
    origins = resolved.cors_origin_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
            expose_headers=["X-Request-ID"],
        )

    app.include_router(auth.router)
    app.include_router(meals.router)
    app.include_router(foods.router)
    app.include_router(glucose.router)
    app.include_router(risk.router)
    app.include_router(foot.router)
    app.add_api_route("/health", health, methods=["GET"], response_model=GatewayHealth)
    return app


async def _check(client: httpx.AsyncClient, url: str, timeout: float) -> ServiceStatus:
    try:
        response = await client.get(f"{url.rstrip('/')}/health", timeout=timeout)
    except httpx.RequestError:
        return "unreachable"
    if response.status_code == 200 and response.json().get("status") == "ok":
        return "ok"
    return "error"


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


app = create_app()
