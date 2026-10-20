import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import c2_glycemic_forecasting.api.routes as forecast_routes
import c2_glycemic_forecasting.model as forecast_model
from c2_glycemic_forecasting.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "c2_glycemic_forecasting"}


def test_forecast_without_body_returns_422() -> None:
    response = client.post("/v1/glucose/forecast")

    assert response.status_code == 422


def test_valid_forecast_returns_16_predictions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_predict_glucose(features: list[float]) -> list[float]:
        assert features == [140, 550, 65, 25, 18, 8]
        return [140.0 + index for index in range(16)]

    monkeypatch.setattr(forecast_routes, "predict_glucose", fake_predict_glucose)

    response = client.post(
        "/v1/glucose/forecast",
        json={
            "premeal_glucose": 140,
            "calories": 550,
            "carbs": 65,
            "protein": 25,
            "fat": 18,
            "fiber": 8,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert len(body["predictions"]) == 16
    assert body["predictions"] == [140.0 + index for index in range(16)]
    assert body["horizon_minutes"] == list(range(15, 241, 15))
    assert body["unit"] == "mg/dL"
    assert body["model_name"] == "GRU"
    assert body["disclaimer"]


def test_forecast_returns_503_when_model_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable_model(features: list[float]) -> list[float]:
        raise FileNotFoundError("Test checkpoint is unavailable")

    monkeypatch.setattr(forecast_routes, "predict_glucose", unavailable_model)

    response = client.post(
        "/v1/glucose/forecast",
        json={
            "premeal_glucose": 140,
            "calories": 550,
            "carbs": 65,
            "protein": 25,
            "fat": 18,
            "fiber": 8,
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "The C2 forecasting model is currently unavailable.",
        "details": [],
    }
    assert body["request_id"]
    assert "predictions" not in body


VALID_REQUEST = {
    "premeal_glucose": 140,
    "calories": 550,
    "carbs": 65,
    "protein": 25,
    "fat": 18,
    "fiber": 8,
}

# Distinctive values, so tests can check they never appear in logs.
DECIMAL_REQUEST = {
    "premeal_glucose": 137.25,
    "calories": 512.5,
    "carbs": 61.75,
    "protein": 23.5,
    "fat": 17.25,
    "fiber": 7.5,
}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("premeal_glucose", 0),
        ("premeal_glucose", -5),
        ("carbs", -1),
        ("carbs", "65"),
        ("calories", True),
        ("fiber", None),
    ],
)
def test_invalid_field_value_returns_422(field: str, value: object) -> None:
    response = client.post("/v1/glucose/forecast", json={**VALID_REQUEST, field: value})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]
    assert all(set(error) == {"field", "issue"} for error in body["error"]["details"])


def test_unknown_field_returns_422() -> None:
    response = client.post("/v1/glucose/forecast", json={**VALID_REQUEST, "sugar": 3})

    assert response.status_code == 422


def test_missing_field_returns_422() -> None:
    request = {key: value for key, value in VALID_REQUEST.items() if key != "fiber"}

    response = client.post("/v1/glucose/forecast", json=request)

    assert response.status_code == 422


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_number_returns_422_without_echoing_input(token: str) -> None:
    body = json.dumps(VALID_REQUEST).replace('"carbs": 65', f'"carbs": {token}')
    assert token in body

    response = client.post(
        "/v1/glucose/forecast",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    # Error details carry the field and the reason only; the rejected value is never echoed.
    assert token not in response.text
    assert all(set(error) == {"field", "issue"} for error in response.json()["error"]["details"])


def test_decimal_values_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_predict_glucose(features: list[float]) -> list[float]:
        assert features == list(DECIMAL_REQUEST.values())
        return [140.0 + index for index in range(16)]

    monkeypatch.setattr(forecast_routes, "predict_glucose", fake_predict_glucose)

    response = client.post("/v1/glucose/forecast", json=DECIMAL_REQUEST)

    assert response.status_code == 200
    assert len(response.json()["predictions"]) == 16


def test_corrupt_checkpoint_returns_503_and_logs_without_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    checkpoint = tmp_path / "corrupt.pt"
    checkpoint.write_text("not a zip archive", encoding="utf-8")
    monkeypatch.setenv("C2_GRU_CHECKPOINT", str(checkpoint))
    forecast_model._load_parameters.cache_clear()

    try:
        with caplog.at_level(logging.ERROR, logger=forecast_routes.LOGGER.name):
            response = client.post("/v1/glucose/forecast", json=DECIMAL_REQUEST)
    finally:
        forecast_model._load_parameters.cache_clear()

    assert response.status_code == 503
    assert "predictions" not in response.json()
    assert any(record.name == forecast_routes.LOGGER.name for record in caplog.records)
    for value in DECIMAL_REQUEST.values():
        assert str(value) not in caplog.text


def test_non_finite_model_output_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def non_finite_model(features: list[float]) -> list[float]:
        raise RuntimeError("The GRU produced non-finite predictions.")

    monkeypatch.setattr(forecast_routes, "predict_glucose", non_finite_model)

    response = client.post("/v1/glucose/forecast", json=VALID_REQUEST)

    assert response.status_code == 503
    assert "predictions" not in response.json()


@pytest.mark.parametrize("error_type", [TypeError, NotImplementedError, RecursionError])
def test_programming_errors_are_not_reported_as_503(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    def broken_model(features: list[float]) -> list[float]:
        raise error_type("Test programming error")

    monkeypatch.setattr(forecast_routes, "predict_glucose", broken_model)

    # The shared RequestContextMiddleware turns unhandled errors into a 500 in the
    # standard envelope, and logs them. These are not model outages, so never a 503.
    response = client.post("/v1/glucose/forecast", json=VALID_REQUEST)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "predictions" not in response.json()
