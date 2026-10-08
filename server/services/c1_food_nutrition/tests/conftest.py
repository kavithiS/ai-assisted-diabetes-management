"""Shared test fixtures.

All images are SYNTHETIC TEST FIXTURES generated in memory with OpenCV. They are not food
photos and imply nothing about model behaviour.
"""

from collections.abc import Callable, Iterator
from typing import Any

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from c1_food_nutrition.config import Settings
from c1_food_nutrition.main import create_app

ANALYZE_URL = "/v1/meals/analyze"

SettingsFactory = Callable[..., Settings]
ImageFactory = Callable[..., bytes]


def _encode(extension: str, width: int, height: int) -> bytes:
    rng = np.random.default_rng(seed=1234)
    pixels = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(extension, pixels)
    assert ok
    return encoded.tobytes()


@pytest.fixture
def make_settings() -> SettingsFactory:
    """Build Settings isolated from any developer ``.env`` file."""

    def factory(**overrides: Any) -> Settings:
        values: dict[str, Any] = {"environment": "test", "log_level": "WARNING"}
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return factory


@pytest.fixture
def settings(make_settings: SettingsFactory) -> Settings:
    return make_settings()


@pytest.fixture
def make_client(make_settings: SettingsFactory) -> Iterator[Callable[..., TestClient]]:
    """Create a TestClient for an app built with the given setting overrides."""
    clients: list[TestClient] = []

    def factory(**overrides: Any) -> TestClient:
        client = TestClient(create_app(make_settings(**overrides)))
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.close()


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


@pytest.fixture
def make_jpeg() -> ImageFactory:
    def factory(width: int = 64, height: int = 48) -> bytes:
        return _encode(".jpg", width, height)

    return factory


@pytest.fixture
def make_png() -> ImageFactory:
    def factory(width: int = 64, height: int = 48) -> bytes:
        return _encode(".png", width, height)

    return factory


@pytest.fixture
def jpeg_bytes(make_jpeg: ImageFactory) -> bytes:
    return make_jpeg()


@pytest.fixture
def png_bytes(make_png: ImageFactory) -> bytes:
    return make_png()
