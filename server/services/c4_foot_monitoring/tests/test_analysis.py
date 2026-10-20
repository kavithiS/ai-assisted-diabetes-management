from collections.abc import Callable

from fastapi.testclient import TestClient

from c4_foot_monitoring.schemas import DISCLAIMER

URL = "/v1/foot/analyze"


def _post(client: TestClient, data: bytes, content_type: str = "image/jpeg") -> dict[str, object]:
    response = client.post(URL, files={"image": ("foot.jpg", data, content_type)})
    return {"status": response.status_code, "body": response.json()}


def _error_code(result: dict[str, object]) -> str:
    body = result["body"]
    assert isinstance(body, dict)
    return str(body["error"]["code"])


def test_mock_analysis_returns_valid_response(client: TestClient, jpeg_bytes: bytes) -> None:
    response = client.post(URL, files={"image": ("foot.jpg", jpeg_bytes, "image/jpeg")})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "analysis_id",
        "classification",
        "risk_band",
        "recommendations",
        "disclaimer",
        "meta",
    }
    assert body["classification"] in {"normal", "ulcer"}
    assert body["risk_band"] in {"Low", "Medium", "High"}
    assert body["recommendations"]
    assert body["disclaimer"] == DISCLAIMER
    assert body["meta"] == {"is_mock": True, "model_name": "mock", "model_version": "0.0.0"}


def test_response_never_contains_confidence(client: TestClient, png_bytes: bytes) -> None:
    response = client.post(URL, files={"image": ("foot.png", png_bytes, "image/png")})

    assert response.status_code == 200
    text = response.text.lower()
    assert "confidence" not in text
    assert "probability" not in text
    assert "score" not in text


def test_mock_cycles_through_every_risk_band(client: TestClient, jpeg_bytes: bytes) -> None:
    bands = [
        client.post(URL, files={"image": ("f.jpg", jpeg_bytes, "image/jpeg")}).json()["risk_band"]
        for _ in range(3)
    ]

    assert bands == ["Low", "Medium", "High"]


def test_missing_image_returns_image_required(client: TestClient) -> None:
    response = client.post(URL, files={"other": ("x.txt", b"hello", "text/plain")})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMAGE_REQUIRED"


def test_empty_image_returns_image_required(client: TestClient) -> None:
    result = _post(client, b"")

    assert result["status"] == 422
    assert _error_code(result) == "IMAGE_REQUIRED"


def test_json_body_returns_unsupported_media_type(client: TestClient) -> None:
    response = client.post(URL, json={"image": "not a file"})

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_non_image_file_returns_unsupported_media_type(client: TestClient) -> None:
    result = _post(client, b"GIF89a fake gif content", "image/gif")

    assert result["status"] == 415
    assert _error_code(result) == "UNSUPPORTED_MEDIA_TYPE"


def test_disallowed_declared_type_returns_unsupported_media_type(
    client: TestClient, jpeg_bytes: bytes
) -> None:
    result = _post(client, jpeg_bytes, "application/pdf")

    assert result["status"] == 415
    assert _error_code(result) == "UNSUPPORTED_MEDIA_TYPE"


def test_truncated_jpeg_returns_image_unreadable(client: TestClient, jpeg_bytes: bytes) -> None:
    result = _post(client, jpeg_bytes[: len(jpeg_bytes) // 2])

    assert result["status"] == 422
    assert _error_code(result) == "IMAGE_UNREADABLE"


def test_too_large_image_returns_413(
    make_client: Callable[..., TestClient], jpeg_bytes: bytes
) -> None:
    small_limit = make_client(max_image_bytes=100, upload_chunk_bytes=32)

    result = _post(small_limit, jpeg_bytes)

    assert result["status"] == 413
    assert _error_code(result) == "IMAGE_TOO_LARGE"


def test_error_envelope_echoes_request_id(client: TestClient) -> None:
    response = client.post(
        URL,
        files={"image": ("foot.jpg", b"", "image/jpeg")},
        headers={"X-Request-ID": "req-123"},
    )

    assert response.json()["request_id"] == "req-123"
    assert set(response.json()["error"]) == {"code", "message", "details"}


def test_missing_weights_fall_back_to_mock(
    make_client: Callable[..., TestClient], jpeg_bytes: bytes
) -> None:
    fallback = make_client(
        foot_model_path="does-not-exist.pth", foot_model_classes=("ulcer", "normal")
    )

    response = fallback.post(URL, files={"image": ("foot.jpg", jpeg_bytes, "image/jpeg")})

    assert response.status_code == 200
    assert response.json()["meta"]["is_mock"] is True
