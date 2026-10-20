"""NumPy inference (API) vs PyTorch (training) parity for the single-step GRU.

Synthetic checkpoints and inputs only. The tests against the configured real checkpoint are
skipped when that file is not present (for example in CI).
"""

import importlib.util
import math
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

import c2_glycemic_forecasting.model as forecast_model
from c2_glycemic_forecasting.api.routes import MODEL_VERSION
from c2_glycemic_forecasting.main import app

TRAINING_DIR = Path(__file__).resolve().parents[1] / "training"
TOLERANCE_MG_DL = 1e-3


def _load_train_gru() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "c2_training_train_gru", TRAINING_DIR / "train_gru.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


train_gru = _load_train_gru()


def synthetic_inputs(count: int = 40) -> np.ndarray:
    rng = np.random.default_rng(7)
    return np.column_stack(
        [
            rng.uniform(60, 250, count),  # premeal glucose, mg/dL
            rng.uniform(0, 1200, count),  # calories
            rng.uniform(0, 150, count),  # carbs
            rng.uniform(0, 80, count),  # protein
            rng.uniform(0, 60, count),  # fat
            rng.uniform(0, 30, count),  # fibre
        ]
    ).astype(np.float32)


def torch_predictions(checkpoint: dict[str, Any], inputs: np.ndarray) -> np.ndarray:
    """The training-time forward pass, exactly as in train_gru.evaluate_model."""
    model = train_gru.GlucoseGRU(6, checkpoint["hidden_size"], 16)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    with torch.no_grad():
        normalized = (torch.from_numpy(inputs) - checkpoint["feature_mean"]) / checkpoint[
            "feature_std"
        ]
        output = model(normalized) * checkpoint["target_std"] + checkpoint["target_mean"]
    predictions: np.ndarray = output.numpy()
    return predictions


def numpy_predictions(inputs: np.ndarray) -> np.ndarray:
    return np.array([forecast_model.predict_glucose(row.tolist()) for row in inputs])


@pytest.fixture
def use_checkpoint(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    forecast_model._load_parameters.cache_clear()
    yield
    forecast_model._load_parameters.cache_clear()


@pytest.fixture
def synthetic_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, use_checkpoint: None
) -> dict[str, Any]:
    """A checkpoint saved with the same structure and file name as train_gru.py."""
    torch.manual_seed(3)
    model = train_gru.GlucoseGRU(6, 32, 16)
    checkpoint: dict[str, Any] = {
        "model_state_dict": model.state_dict(),
        "feature_columns": train_gru.FEATURE_COLUMNS,
        "target_columns": train_gru.TARGET_COLUMNS,
        "feature_mean": torch.tensor([110.0, 550.0, 60.0, 30.0, 20.0, 10.0]),
        "feature_std": torch.tensor([30.0, 300.0, 40.0, 20.0, 15.0, 8.0]),
        "target_mean": torch.linspace(120.0, 105.0, 16),
        "target_std": torch.linspace(20.0, 35.0, 16),
        "hidden_size": 32,
        "best_epoch": 1,
        "validation_metrics": {"mae_mg_dl": 0.0, "rmse_mg_dl": 0.0},
    }
    path = tmp_path / "gru_best.pt"
    torch.save(checkpoint, path)
    monkeypatch.setenv("C2_GRU_CHECKPOINT", str(path))
    return checkpoint


def test_numpy_loader_maps_every_checkpoint_tensor(synthetic_checkpoint: dict[str, Any]) -> None:
    state = synthetic_checkpoint["model_state_dict"]
    assert isinstance(state, dict)
    expected = [
        state["gru.weight_ih_l0"],
        state["gru.weight_hh_l0"],
        state["gru.bias_ih_l0"],
        state["gru.bias_hh_l0"],
        state["output_layer.weight"],
        state["output_layer.bias"],
        synthetic_checkpoint["feature_mean"],
        synthetic_checkpoint["feature_std"],
        synthetic_checkpoint["target_mean"],
        synthetic_checkpoint["target_std"],
    ]

    parameters = forecast_model._load_parameters()

    for storage_id, tensor in enumerate(expected):
        assert isinstance(tensor, torch.Tensor)
        assert np.array_equal(parameters[storage_id], tensor.numpy()), storage_id


def test_numpy_matches_pytorch_on_synthetic_checkpoint(
    synthetic_checkpoint: dict[str, Any],
) -> None:
    inputs = synthetic_inputs()

    difference = np.abs(numpy_predictions(inputs) - torch_predictions(synthetic_checkpoint, inputs))

    assert difference.max() < TOLERANCE_MG_DL


def test_default_checkpoint_is_the_corrected_model() -> None:
    path = forecast_model.DEFAULT_CHECKPOINT

    assert path.parent.name == "results_single_step_gru_final"
    assert path.parent.parent.name == "CGMacros_C2_processed_premeal_fix"


configured = forecast_model.DEFAULT_CHECKPOINT
needs_real_checkpoint = pytest.mark.skipif(
    not configured.is_file(), reason=f"Checkpoint not available on this machine: {configured}"
)


@needs_real_checkpoint
def test_numpy_matches_pytorch_on_configured_checkpoint(
    monkeypatch: pytest.MonkeyPatch, use_checkpoint: None
) -> None:
    monkeypatch.delenv("C2_GRU_CHECKPOINT", raising=False)
    checkpoint = torch.load(configured, map_location="cpu", weights_only=True)
    assert tuple(checkpoint["feature_columns"]) == train_gru.FEATURE_COLUMNS
    assert checkpoint["hidden_size"] == 32 and len(checkpoint["target_columns"]) == 16
    inputs = synthetic_inputs()

    difference = np.abs(numpy_predictions(inputs) - torch_predictions(checkpoint, inputs))

    assert difference.max() < TOLERANCE_MG_DL


@needs_real_checkpoint
def test_api_returns_16_finite_predictions_from_configured_checkpoint(
    monkeypatch: pytest.MonkeyPatch, use_checkpoint: None
) -> None:
    monkeypatch.delenv("C2_GRU_CHECKPOINT", raising=False)
    meal = {
        "premeal_glucose": 112.0,
        "calories": 620.0,
        "carbs": 72.5,
        "protein": 26.0,
        "fat": 21.0,
        "fiber": 6.5,
    }

    response = TestClient(app).post("/v1/glucose/forecast", json=meal)

    assert response.status_code == 200
    body = response.json()
    assert len(body["predictions"]) == 16
    assert all(isinstance(value, float) and math.isfinite(value) for value in body["predictions"])
    assert body["horizon_minutes"] == list(range(15, 241, 15))
    assert body["unit"] == "mg/dL"
    assert body["model_name"] == "GRU"
    assert body["model_version"] == MODEL_VERSION
    expected = numpy_predictions(np.array([list(meal.values())], dtype=np.float32))[0]
    assert np.allclose(body["predictions"], expected)
