from fastapi.testclient import TestClient

from c1_food_nutrition.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "c1_food_nutrition"}
