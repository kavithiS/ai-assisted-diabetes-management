from fastapi.testclient import TestClient

from c4_foot_monitoring.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "c4_foot_monitoring"}
