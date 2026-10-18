"""Tests for startup behaviour of the C1 service (model pre-loading)."""

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from c1_food_nutrition.api.deps import _load_trained_recognizer
from c1_food_nutrition.main import create_app

SettingsFactory = Callable[..., object]
BundleFactory = Callable[..., Path]


def test_mock_recognizer_startup_does_not_load_model(
    make_client: Callable[..., TestClient],
) -> None:
    """When RECOGNIZER=mock the startup event does nothing (no PyTorch needed)."""
    _load_trained_recognizer.cache_clear()
    client = make_client(recognizer="mock")
    with client:
        response = client.get("/health")
    assert response.status_code == 200
    assert _load_trained_recognizer.cache_info().currsize == 0


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("torch"),
    reason="PyTorch not installed",
)
def test_torch_recognizer_loaded_before_first_request(
    make_bundle: BundleFactory,
    make_client: Callable[..., TestClient],
) -> None:
    """When RECOGNIZER=torch the model is in the cache before any request arrives."""
    _load_trained_recognizer.cache_clear()
    bundle = make_bundle()
    with TestClient(
        create_app(
            __import__("c1_food_nutrition.config", fromlist=["Settings"]).Settings(
                _env_file=None,
                environment="test",
                log_level="WARNING",
                recognizer="torch",
                model_path=bundle,
            )
        )
    ):
        assert _load_trained_recognizer.cache_info().currsize == 1
