"""Proxy behaviour: routes, identity headers, timeouts and error envelopes (ADR 0005)."""

import uuid
from collections.abc import Callable
from typing import Any

import httpx
import pytest

# Same values as in conftest.py (test fixtures, not secrets).
INTERNAL_TOKEN = "test-internal-token"
DEMO_PATIENT = uuid.UUID("00000000-0000-4000-8000-000000000001")


GatewayFactory = Callable[..., Any]


def open_gateway(make_gateway: GatewayFactory, **kwargs: Any) -> Any:
    """A gateway with login switched off: every request is the demo patient."""
    return make_gateway(auth_required=False, demo_patient_id=DEMO_PATIENT, **kwargs)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_bare_meals_path_is_forwarded_without_redirect(
    make_gateway: GatewayFactory, method: str
) -> None:
    gateway = open_gateway(make_gateway)

    response = gateway.client.request(method, "/api/v1/meals", params={"limit": "5"})

    assert response.status_code == 200
    assert len(gateway.seen) == 1
    assert gateway.seen[0].method == method
    assert gateway.seen[0].url.path == "/v1/meals"
    assert gateway.seen[0].url.params["limit"] == "5"


@pytest.mark.parametrize(
    ("method", "path", "upstream"),
    [
        ("POST", "/api/v1/meals/analyze", "/v1/meals/analyze"),
        ("GET", "/api/v1/meals/7", "/v1/meals/7"),
        ("DELETE", "/api/v1/meals/7", "/v1/meals/7"),
        ("GET", "/api/v1/meals/summary", "/v1/meals/summary"),
        ("GET", "/api/v1/foods", "/v1/foods"),
        ("POST", "/api/v1/glucose/forecast", "/v1/glucose/forecast"),
        ("POST", "/api/v1/risk/assess", "/v1/risk/assess"),
        ("POST", "/api/v1/foot/analyze", "/v1/foot/analyze"),
    ],
)
def test_paths_are_forwarded_to_the_right_service(
    make_gateway: GatewayFactory,
    method: str,
    path: str,
    upstream: str,
) -> None:
    gateway = open_gateway(make_gateway)

    response = gateway.client.request(method, path)

    assert response.status_code == 200
    assert [r.url.path for r in gateway.seen] == [upstream]


def test_the_gateway_sets_identity_and_ignores_what_the_client_sends(
    make_gateway: GatewayFactory,
) -> None:
    gateway = open_gateway(make_gateway)

    gateway.client.get(
        "/api/v1/meals",
        headers={
            "X-Patient-Id": "99999999-9999-4999-8999-999999999999",
            "X-Internal-Token": "guessed",
            "Authorization": "Bearer whatever",
            "X-Request-ID": "client-request-id",
        },
    )

    sent = gateway.seen[0].headers
    assert sent["x-patient-id"] == str(DEMO_PATIENT)
    assert sent["x-internal-token"] == INTERNAL_TOKEN
    assert "authorization" not in sent
    assert sent["x-request-id"] == "client-request-id"  # a safe id is reused, not trusted


def test_signed_in_patient_id_is_forwarded(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()
    user_id = gateway.add_user()

    response = gateway.client.get("/api/v1/meals", headers=gateway.bearer())

    assert response.status_code == 200
    assert gateway.seen[0].headers["x-patient-id"] == str(user_id)


def test_requests_without_a_token_are_refused(make_gateway: GatewayFactory) -> None:
    gateway = make_gateway()

    response = gateway.client.get("/api/v1/meals")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert gateway.seen == []


def test_login_off_without_a_demo_patient_is_a_configuration_error(
    make_gateway: GatewayFactory,
) -> None:
    gateway = make_gateway(auth_required=False)

    response = gateway.client.get("/api/v1/meals")

    assert response.status_code == 503
    assert gateway.seen == []


def test_analyze_gets_the_long_timeout_and_other_calls_the_short_one(
    make_gateway: GatewayFactory,
) -> None:
    gateway = open_gateway(make_gateway)

    gateway.client.post("/api/v1/meals/analyze")
    gateway.client.get("/api/v1/meals")

    assert gateway.seen[0].extensions["timeout"]["read"] == 65.0
    assert gateway.seen[1].extensions["timeout"]["read"] == 15.0


def test_slow_service_gives_504_in_the_error_envelope(make_gateway: GatewayFactory) -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    response = open_gateway(make_gateway, handler=slow).client.get("/api/v1/meals")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


def test_unreachable_service_gives_502_in_the_error_envelope(make_gateway: GatewayFactory) -> None:
    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    response = open_gateway(make_gateway, handler=refused).client.get("/api/v1/meals")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"


def test_service_errors_are_relayed_unchanged(make_gateway: GatewayFactory) -> None:
    def not_found(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"code": "NOT_FOUND"}})

    response = open_gateway(make_gateway, handler=not_found).client.get("/api/v1/meals/1")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "NOT_FOUND"}}


def test_oversized_body_is_refused_before_it_is_forwarded(make_gateway: GatewayFactory) -> None:
    gateway = open_gateway(make_gateway, max_request_bytes=1000)

    response = gateway.client.post("/api/v1/meals/analyze", content=b"x" * 5000)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert gateway.seen == []
