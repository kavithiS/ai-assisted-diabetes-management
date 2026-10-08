from collections.abc import AsyncIterator, Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from diacare_gateway.main import app
from diacare_gateway.routes import get_http_client

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def _client_with(handler: Handler) -> TestClient:
    async def override() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    app.dependency_overrides[get_http_client] = override
    return TestClient(app)


def test_health_reports_all_services_ok() -> None:
    client = _client_with(lambda request: httpx.Response(200, json={"status": "ok"}))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "diacare_gateway"
    assert body["services"] == {
        "c1_food_nutrition": "ok",
        "c2_glycemic_forecasting": "ok",
        "c3_risk_xai": "ok",
        "c4_foot_monitoring": "ok",
    }


def test_health_reports_unreachable_service_as_degraded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.port == 8003:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, json={"status": "ok"})

    response = _client_with(handler).get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"]["c3_risk_xai"] == "unreachable"
