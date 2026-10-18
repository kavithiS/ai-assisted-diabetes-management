"""CORS is off unless CORS_ORIGINS lists the browser origins allowed to call the gateway."""

from collections.abc import Callable
from typing import Any

GatewayFactory = Callable[..., Any]

ORIGIN = "http://localhost:5600"


def test_no_cors_by_default(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()

    response = gateway.client.get("/health", headers={"Origin": ORIGIN})

    assert "access-control-allow-origin" not in response.headers


def test_listed_origin_is_allowed(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway(cors_origins=f"{ORIGIN}/, http://other.test")

    preflight = gateway.client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == ORIGIN


def test_unlisted_origin_is_refused(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway(cors_origins=ORIGIN)

    response = gateway.client.get("/health", headers={"Origin": "http://evil.test"})

    assert "access-control-allow-origin" not in response.headers
