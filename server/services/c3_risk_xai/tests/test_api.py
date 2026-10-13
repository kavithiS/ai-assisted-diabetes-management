"""HTTP tests for POST /v1/risk/assess and GET /v1/risk/status (stand-in models)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from c3_risk_xai.main import app
from c3_risk_xai.ml import predict
from c3_risk_xai.ml.predict import EXAMPLE_PATIENT
from c3_risk_xai.settings import get_settings


@pytest.fixture
def api(fake_models: Path) -> Iterator[TestClient]:
    # The context manager runs the lifespan, which loads the stand-in bundles.
    with TestClient(app) as client:
        yield client


@pytest.mark.slow
def test_assess_ok_has_no_probability_for_patients(api: TestClient) -> None:
    response = api.post("/v1/risk/assess", json=EXAMPLE_PATIENT)
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["risk_category"] in {"Low", "Moderate", "High"}
    assert "not a diagnosis" in body["disclaimer"]
    assert "debug" not in body
    assert "risk_probability" not in response.text


@pytest.mark.slow
def test_debug_needs_research_mode(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert "debug" not in api.post("/v1/risk/assess?debug=true", json=EXAMPLE_PATIENT).json()

    monkeypatch.setenv("C3_RESEARCH_MODE", "true")
    get_settings.cache_clear()
    try:
        body = api.post("/v1/risk/assess?debug=true", json=EXAMPLE_PATIENT).json()
        assert 0.0 <= body["debug"]["risk_probability"] <= 1.0
        assert set(body["debug"]["thresholds"]) == {"low_max", "high_min"}
    finally:
        get_settings.cache_clear()


def test_insufficient_and_invalid_statuses(api: TestClient) -> None:
    missing = api.post("/v1/risk/assess", json={"age": 50, "bmi": 30}).json()
    invalid = api.post("/v1/risk/assess", json=dict(EXAMPLE_PATIENT, bmi=500)).json()

    assert missing["status"] == "insufficient_data"
    assert "risk_category" not in missing
    assert set(missing["missing_critical_fields"]) == {"systolic_bp", "diastolic_bp"}
    assert invalid["status"] == "invalid_input"
    assert invalid["problems"]


def test_wrong_types_and_unknown_fields_are_422(api: TestClient) -> None:
    assert api.post("/v1/risk/assess", json={"age": "old"}).status_code == 422
    assert api.post("/v1/risk/assess", json={"cholesterol": 5}).status_code == 422


def test_status_reports_loaded_models(api: TestClient) -> None:
    body = api.get("/v1/risk/status").json()

    assert body["model_loaded"] is True
    assert set(body["models"]) == {"without_glucose", "with_glucose"}


def test_missing_models_give_503_not_a_crash(
    fake_models: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(predict, "MODEL_DIR", tmp_path)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/v1/risk/status").json()["model_loaded"] is False
        assert client.post("/v1/risk/assess", json=EXAMPLE_PATIENT).status_code == 503
    predict.load_bundle.cache_clear()
