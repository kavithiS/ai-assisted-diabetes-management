"""Tests for classifier loading and the `/v1/glucose/dietary-risk` endpoint.

Classifiers here are small real XGBoost models trained on synthetic data in a temporary folder.
The test against the deployed artefacts is skipped when they are not present (for example in CI).
"""

import hashlib
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import xgboost as xgb
from fastapi.testclient import TestClient

import c2_glycemic_forecasting.api.routes as routes
from c2_glycemic_forecasting import dietary_risk
from c2_glycemic_forecasting.main import app
from c2_glycemic_forecasting.trajectory_features import FEATURE_NAMES, build_feature_row

client = TestClient(app)

VALID_REQUEST = {
    "premeal_glucose": 140,
    "calories": 550,
    "carbs": 65,
    "protein": 25,
    "fat": 18,
    "fiber": 8,
}
RISING = [140.0 + 4 * step for step in range(1, 17)]  # peaks at 204 mg/dL at +240 min
PEAK_INDEX = FEATURE_NAMES.index("predicted_peak_glucose")


def write_classifier(directory: Path, **metadata_overrides: Any) -> dict[str, Any]:
    """Train a tiny model whose output rises with the predicted peak; write it with metadata."""
    rng = np.random.default_rng(0)
    features = rng.uniform(0, 300, size=(200, len(FEATURE_NAMES)))
    labels = (features[:, PEAK_INDEX] > 180).astype(int)
    booster = xgb.train(
        {"objective": "binary:logistic", "max_depth": 2, "seed": 0, "nthread": 1},
        xgb.DMatrix(features, label=labels, feature_names=list(FEATURE_NAMES)),
        num_boost_round=20,
    )
    directory.mkdir(parents=True, exist_ok=True)
    model_path = directory / dietary_risk.MODEL_FILE
    booster.save_model(model_path)
    metadata: dict[str, Any] = {
        "model_name": "XGBoost",
        "model_version": "xgb-test",
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "feature_names": list(FEATURE_NAMES),
        "decision_threshold": 0.5,
        "label_name": "above_180_within_4h",
        "label_definition": "test definition",
        "evaluation_note": "Synthetic test model.",
    }
    metadata.update(metadata_overrides)
    (directory / dietary_risk.METADATA_FILE).write_text(json.dumps(metadata), encoding="utf-8")
    return metadata


@pytest.fixture(autouse=True)
def clear_classifier_cache() -> Iterator[None]:
    dietary_risk.load_classifier.cache_clear()
    yield
    dietary_risk.load_classifier.cache_clear()


@pytest.fixture
def model_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "classifier"
    monkeypatch.setenv("C2_DIETARY_RISK_MODEL_DIR", str(directory))
    return directory


@pytest.fixture
def fake_gru(monkeypatch: pytest.MonkeyPatch) -> list[list[float]]:
    calls: list[list[float]] = []

    def predict(features: list[float]) -> list[float]:
        calls.append(list(features))
        return RISING

    monkeypatch.setattr(routes, "predict_glucose", predict)
    return calls


# --- loading ------------------------------------------------------------------------------


def test_load_classifier_reads_valid_artefacts(model_dir: Path) -> None:
    write_classifier(model_dir)

    classifier = dietary_risk.load_classifier()

    assert classifier.model_version == "xgb-test"
    assert classifier.threshold == 0.5


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"model_sha256": "0" * 64}, "does not match"),
        ({"feature_names": list(reversed(FEATURE_NAMES))}, "features do not match"),
        ({"label_name": "other"}, "different label"),
        ({"decision_threshold": 1.5}, "threshold"),
        ({"decision_threshold": "0.5"}, "decision_threshold"),
        ({"model_version": None}, "model_version"),
    ],
)
def test_load_classifier_rejects_inconsistent_metadata(
    model_dir: Path, override: dict[str, Any], message: str
) -> None:
    write_classifier(model_dir, **override)

    with pytest.raises(dietary_risk.ClassifierUnavailableError, match=message):
        dietary_risk.load_classifier()


def test_load_classifier_rejects_missing_files(model_dir: Path) -> None:
    with pytest.raises(dietary_risk.ClassifierUnavailableError, match="Cannot read"):
        dietary_risk.load_classifier()


def test_load_classifier_rejects_corrupt_model(model_dir: Path) -> None:
    write_classifier(model_dir)
    model_path = model_dir / dietary_risk.MODEL_FILE
    model_path.write_bytes(b"{not a model")
    metadata_path = model_dir / dietary_risk.METADATA_FILE
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(dietary_risk.ClassifierUnavailableError, match="invalid"):
        dietary_risk.load_classifier()


def test_classifier_requires_features_in_order(model_dir: Path) -> None:
    write_classifier(model_dir)
    classifier = dietary_risk.load_classifier()
    row = build_feature_row(140, 550, 65, 25, 18, 8, RISING)

    with pytest.raises(ValueError, match="order"):
        classifier.estimate_above_threshold(dict(reversed(list(row.items()))))


def test_classifier_accepts_missing_carb_fraction_when_calories_are_zero(model_dir: Path) -> None:
    write_classifier(model_dir)
    row = build_feature_row(140, 0, 0, 0, 0, 0, RISING)

    assert np.isnan(row["carb_energy_fraction"])
    assert isinstance(dietary_risk.load_classifier().estimate_above_threshold(row), bool)


# --- endpoint -----------------------------------------------------------------------------


def test_dietary_risk_returns_trajectory_features_and_indicator(
    model_dir: Path, fake_gru: list[list[float]]
) -> None:
    write_classifier(model_dir)

    response = client.post("/v1/glucose/dietary-risk", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert fake_gru == [[140, 550, 65, 25, 18, 8]]
    assert body["predictions"] == RISING
    assert body["horizon_minutes"] == list(range(15, 241, 15))
    assert body["unit"] == "mg/dL"
    assert body["trajectory_features"] == {
        "predicted_peak_glucose": 204.0,
        "predicted_peak_minutes": 240,
        "peak_change_from_premeal": 64.0,
        "max_rise": 64.0,
        "max_rise_rate": pytest.approx(4 / 15),
        "predicted_iauc": pytest.approx(sum(4 * k + 2 for k in range(16)) * 15),
    }
    indicator = body["response_indicator"]
    assert indicator["name"] == "above_180_within_4h"
    assert indicator["status"] == "available"
    assert indicator["estimated_above_180"] is True  # synthetic model: peak 204 > 180
    assert indicator["model_version"] == "xgb-test"
    assert indicator["evaluation_note"] == "Synthetic test model."
    assert "180 mg/dL" in indicator["definition"]
    assert body["forecast_model_name"] == "GRU"
    assert "not a medical diagnosis" in body["disclaimer"]


def test_dietary_risk_never_returns_a_score_or_probability(
    model_dir: Path, fake_gru: list[list[float]]
) -> None:
    write_classifier(model_dir)

    body = client.post("/v1/glucose/dietary-risk", json=VALID_REQUEST).json()

    text = json.dumps(body).lower()
    assert "probab" not in text
    assert "score" not in text
    assert "confidence" not in text


def test_dietary_risk_negative_estimate(model_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_classifier(model_dir)
    monkeypatch.setattr(routes, "predict_glucose", lambda features: [120.0] * 16)

    body = client.post("/v1/glucose/dietary-risk", json=VALID_REQUEST).json()

    assert body["response_indicator"]["estimated_above_180"] is False
    assert body["trajectory_features"]["max_rise"] == 0


def test_dietary_risk_reports_unavailable_classifier_without_inventing_a_value(
    model_dir: Path, fake_gru: list[list[float]], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        response = client.post("/v1/glucose/dietary-risk", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["predictions"] == RISING
    indicator = body["response_indicator"]
    assert indicator["status"] == "unavailable"
    assert indicator["estimated_above_180"] is None
    assert indicator["model_version"] is None
    assert indicator["evaluation_note"] is None
    assert "ClassifierUnavailableError" in caplog.text
    # Patient values never reach the logs.
    assert "550" not in caplog.text


def test_dietary_risk_returns_503_when_gru_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, model_dir: Path
) -> None:
    write_classifier(model_dir)

    def unavailable(features: list[float]) -> list[float]:
        raise FileNotFoundError("missing checkpoint")

    monkeypatch.setattr(routes, "predict_glucose", unavailable)

    response = client.post("/v1/glucose/dietary-risk", json=VALID_REQUEST)

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "The C2 forecasting model is currently unavailable.",
        "details": [],
    }
    assert response.json()["request_id"]


@pytest.mark.parametrize(
    "change",
    [
        {"carbs": "65"},
        {"premeal_glucose": True},
        {"premeal_glucose": 0},
        {"fat": -1},
        {"extra": 1},
        {"fiber": None},
    ],
)
def test_dietary_risk_rejects_invalid_requests(
    change: dict[str, Any], fake_gru: list[list[float]]
) -> None:
    response = client.post("/v1/glucose/dietary-risk", json={**VALID_REQUEST, **change})

    assert response.status_code == 422
    assert fake_gru == []


def test_dietary_risk_rejects_missing_field_and_nan(fake_gru: list[list[float]]) -> None:
    missing = {key: value for key, value in VALID_REQUEST.items() if key != "premeal_glucose"}
    assert client.post("/v1/glucose/dietary-risk", json=missing).status_code == 422

    body = json.dumps(VALID_REQUEST).replace("140", "NaN")
    response = client.post(
        "/v1/glucose/dietary-risk", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert fake_gru == []


def test_forecast_endpoint_is_unchanged_by_dietary_risk(fake_gru: list[list[float]]) -> None:
    body = client.post("/v1/glucose/forecast", json=VALID_REQUEST).json()

    assert set(body) == {
        "predictions",
        "horizon_minutes",
        "unit",
        "model_name",
        "model_version",
        "disclaimer",
    }
    assert body["predictions"] == RISING


# --- deployed artefacts -------------------------------------------------------------------

DEPLOYED_DIR = dietary_risk.DEFAULT_MODEL_DIR


@pytest.mark.skipif(
    not (DEPLOYED_DIR / dietary_risk.MODEL_FILE).is_file(),
    reason="Deployed classifier artefacts are not available.",
)
def test_deployed_artefacts_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("C2_DIETARY_RISK_MODEL_DIR", raising=False)
    from c2_glycemic_forecasting import model as gru_model

    if not gru_model._checkpoint_path().is_file():
        pytest.skip("Deployed GRU checkpoint is not available.")

    response = client.post("/v1/glucose/dietary-risk", json=VALID_REQUEST)

    assert response.status_code == 200
    indicator = response.json()["response_indicator"]
    assert indicator["status"] == "available"
    assert isinstance(indicator["estimated_above_180"], bool)
    assert indicator["model_version"].startswith("xgb-above180-4h-")
