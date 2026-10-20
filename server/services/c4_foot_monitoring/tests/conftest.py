from collections.abc import Callable, Iterator

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from c4_foot_monitoring.config import Settings
from c4_foot_monitoring.main import create_app


def encode(extension: str, size: int = 32) -> bytes:
    """A small synthetic image (random pixels), encoded as JPEG or PNG."""
    rng = np.random.default_rng(0)
    pixels = rng.integers(0, 256, size=(size, size, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(extension, pixels)
    assert ok
    return bytes(buffer.tobytes())


@pytest.fixture
def jpeg_bytes() -> bytes:
    return encode(".jpg")


@pytest.fixture
def png_bytes() -> bytes:
    return encode(".png")


@pytest.fixture
def make_client() -> Iterator[Callable[..., TestClient]]:
    """Build a test client with explicit settings (mock classifier unless told otherwise)."""
    clients: list[TestClient] = []

    def factory(**overrides: object) -> TestClient:
        settings = Settings(environment="test", **overrides)  # type: ignore[arg-type]
        client = TestClient(create_app(settings))
        client.__enter__()  # runs the lifespan, which loads the classifier
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()
