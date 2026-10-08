from fastapi.testclient import TestClient

from c2_glycemic_forecasting.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "c2_glycemic_forecasting"}


def test_placeholder_route_returns_501() -> None:
    response = client.post("/v1/glucose/forecast")

    assert response.status_code == 501
