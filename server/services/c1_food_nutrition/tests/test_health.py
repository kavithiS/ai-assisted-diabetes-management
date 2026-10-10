from fastapi.testclient import TestClient

from c1_food_nutrition.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "c1_food_nutrition"}


def test_placeholder_route_returns_501() -> None:
    response = client.post("/v1/meals/analyze")

    assert response.status_code == 501
