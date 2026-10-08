from fastapi.testclient import TestClient

from c3_risk_xai.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "c3_risk_xai"}


def test_placeholder_route_returns_501() -> None:
    response = client.post("/v1/risk/assess")

    assert response.status_code == 501
