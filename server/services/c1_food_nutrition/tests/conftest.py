"""Shared test fixtures.

All images are SYNTHETIC TEST FIXTURES generated in memory with OpenCV. They are not food
photos and imply nothing about model behaviour.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
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


BundleFactory = Callable[..., Path]


@pytest.fixture
def make_bundle(tmp_path: Path) -> BundleFactory:
    """Write a model bundle with RANDOM weights (a test fixture, not a trained model).

    Skips the test when PyTorch or torchvision is not installed.
    """
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    from c1_food_nutrition.ml.bundle import BUNDLE_FORMAT, build_network

    def factory(
        classes: tuple[str, ...] = ("kiribath", "lunu_miris", "hoppers"),
        threshold: float = 0.0,
        size: int = 64,
        n_outputs: int | None = None,
        **overrides: Any,
    ) -> Path:
        torch.manual_seed(0)
        net = build_network("mobilenet_v3_large", n_outputs or len(classes))
        bundle: dict[str, Any] = {
            "format": BUNDLE_FORMAT,
            "arch": "mobilenet_v3_large",
            "state": net.state_dict(),
            "classes": list(classes),
            "size": size,
            "threshold": threshold,
            "run": "fixture-random-weights",
        }
        bundle.update(overrides)
        path = tmp_path / "bundle.pt"
        torch.save(bundle, path)
        return path

    return factory


TableFactory = Callable[..., Path]

TABLE_HEADER = (
    "food_id,food_name,category,serving_size_g,energy_kcal,carbohydrate_g,fat_g,protein_g,"
    "fibre_g,sodium_mg,source,source_url"
)
# TEST FIXTURE rows with made-up round numbers. They are not nutrition data.
SL = "Sri Lankan Food Composition Database"
TABLE_ROWS = (
    f"SL_9,Fixture Milk Rice,x,,100,20,2,3,1,200,{SL},",
    f"SL_37,Fixture Hoppers,x,,150,30,1,2.5,,300,{SL},",  # fibre unknown
    f"SL_99,Fixture Zero,x,,0,0,0,0,0,0,{SL},",  # real zeros stay zero
    "BD_1,Fixture Regional Food,x,,999,99,9,9,9,999,Food Composition Table for Bangladesh (2013),",
    'US_1,Fixture USDA Food,x,,50,5,0.5,1,0.5,5,"USDA FoodData Central, Foundation Foods",',
)


@pytest.fixture
def make_table(tmp_path: Path) -> TableFactory:
    """Write a small composition table (TEST FIXTURE values) and return its path."""

    def factory(header: str = TABLE_HEADER, rows: tuple[str, ...] = TABLE_ROWS) -> Path:
        path = tmp_path / "table.csv"
        path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
        return path

    return factory
