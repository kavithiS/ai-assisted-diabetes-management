"""Integration tests for POST /v1/meals/analyze (ADR 0004).

Images are synthetic fixtures; the endpoint is in MOCK mode during Phase 0.
"""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from c1_food_nutrition.api.deps import get_clock, get_meal_analysis_service
from c1_food_nutrition.schemas.common import ErrorResponse
from c1_food_nutrition.schemas.meal_analysis import MealAnalysisResponse
from c1_food_nutrition.services.pipeline import MOCK_WARNING

URL = "/v1/meals/analyze"
FIXED_NOW = datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC)

ClientFactory = Callable[..., TestClient]
FileTuple = tuple[str | None, bytes | str, str | None]


def post_meal(
    client: TestClient,
    image: FileTuple | None,
    **fields: str,
) -> httpx.Response:
    """POST a multipart request. Metadata fields are sent as multipart parts too."""
    files: dict[str, Any] = {name: (None, value) for name, value in fields.items()}
    if image is not None:
        files["image"] = image
    if not files:  # force a multipart body even with no parts
        files["unused"] = (None, "")
    response: httpx.Response = client.post(URL, files=files)
    return response


def assert_error(response: httpx.Response, status: int, code: str) -> dict[str, Any]:
    """Check status, the standard error envelope, and request-id correlation."""
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    ErrorResponse.model_validate(body)
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["request_id"] == response.headers["X-Request-ID"]
    return body


@pytest.fixture
def fixed_clock_client(client: TestClient) -> Iterator[TestClient]:
    client.app.dependency_overrides[get_clock] = lambda: lambda: FIXED_NOW  # type: ignore[attr-defined]
    yield client
    client.app.dependency_overrides.clear()  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- happy paths


def test_jpeg_returns_mock_analysis(client: TestClient, jpeg_bytes: bytes) -> None:
    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"))

    assert response.status_code == 200, response.text
    result = MealAnalysisResponse.model_validate(response.json())
    assert result.meta.is_mock is True
    assert MOCK_WARNING in result.meta.warnings
    assert result.meta.request_id == response.headers["X-Request-ID"]
    assert result.image.media_type == "image/jpeg"
    assert (result.image.width, result.image.height) == (64, 48)
    assert result.image.size_bytes == len(jpeg_bytes)
    assert len(result.items) == 2
    assert result.metadata.meal_type is None
    assert result.metadata.captured_at is None
    assert result.metadata.reference_object is None
    assert "Not a diagnostic" in result.disclaimer


def test_totals_are_sum_of_items(client: TestClient, jpeg_bytes: bytes) -> None:
    result = MealAnalysisResponse.model_validate(
        post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg")).json()
    )
    expected = sum(item.nutrition.carbohydrate_g or 0.0 for item in result.items)
    assert result.totals.carbohydrate_g == pytest.approx(expected)


def test_png_is_accepted(client: TestClient, png_bytes: bytes) -> None:
    response = post_meal(client, ("meal.png", png_bytes, "image/png"))
    assert response.status_code == 200, response.text
    assert response.json()["image"]["media_type"] == "image/png"


def test_metadata_is_validated_and_echoed(
    fixed_clock_client: TestClient, jpeg_bytes: bytes
) -> None:
    reference = "  A4 sheet / ස්කේල් 30cm  "
    response = post_meal(
        fixed_clock_client,
        ("meal.jpg", jpeg_bytes, "image/jpeg"),
        meal_type="lunch",
        captured_at="2026-10-03T12:30:00+05:30",
        reference_object=reference,
    )

    assert response.status_code == 200, response.text
    metadata = response.json()["metadata"]
    assert metadata["meal_type"] == "lunch"
    assert metadata["captured_at"] == "2026-10-03T07:00:00Z"  # normalised to UTC
    assert metadata["reference_object"] == reference  # passed through unchanged


@pytest.mark.parametrize(
    "captured_at",
    [
        "2001-01-01T00:00:00Z",  # far past stays valid
        "2026-10-03T12:04:59Z",  # inside the 300 s skew window
        "2026-10-03T07:00:00.123456-05:00",
    ],
)
def test_captured_at_accepted(
    fixed_clock_client: TestClient, jpeg_bytes: bytes, captured_at: str
) -> None:
    response = post_meal(
        fixed_clock_client, ("meal.jpg", jpeg_bytes, "image/jpeg"), captured_at=captured_at
    )
    assert response.status_code == 200, response.text


def test_png_bytes_with_other_allowed_content_type_use_detected_type(
    client: TestClient, png_bytes: bytes
) -> None:
    response = post_meal(client, ("meal.jpg", png_bytes, "image/jpeg"))
    assert response.status_code == 200, response.text
    assert response.json()["image"]["media_type"] == "image/png"


def test_image_jpg_alias_is_accepted(client: TestClient, jpeg_bytes: bytes) -> None:
    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpg"))
    assert response.status_code == 200, response.text


def test_image_exactly_at_size_limit_is_accepted(
    make_client: ClientFactory, jpeg_bytes: bytes
) -> None:
    client = make_client(max_image_bytes=len(jpeg_bytes))
    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"))
    assert response.status_code == 200, response.text


# --------------------------------------------------------------------------- IMAGE_REQUIRED


def test_missing_image(client: TestClient) -> None:
    body = assert_error(post_meal(client, None, meal_type="lunch"), 422, "IMAGE_REQUIRED")
    assert body["error"]["details"][0]["field"] == "image"


def test_empty_image_file(client: TestClient) -> None:
    assert_error(post_meal(client, ("meal.jpg", b"", "image/jpeg")), 422, "IMAGE_REQUIRED")


def test_image_sent_as_text_field(client: TestClient) -> None:
    assert_error(post_meal(client, (None, "not a file", None)), 422, "IMAGE_REQUIRED")


# --------------------------------------------------------------------------- UNSUPPORTED_MEDIA_TYPE


def test_json_body_is_rejected(client: TestClient) -> None:
    assert_error(client.post(URL, json={"image": "abc"}), 415, "UNSUPPORTED_MEDIA_TYPE")


def test_urlencoded_body_is_rejected(client: TestClient) -> None:
    assert_error(client.post(URL, data={"meal_type": "lunch"}), 415, "UNSUPPORTED_MEDIA_TYPE")


def test_request_without_content_type_is_rejected(client: TestClient) -> None:
    assert_error(client.post(URL), 415, "UNSUPPORTED_MEDIA_TYPE")


def test_multipart_without_boundary_is_malformed(client: TestClient) -> None:
    response = client.post(URL, content=b"abc", headers={"content-type": "multipart/form-data"})
    assert_error(response, 400, "MALFORMED_REQUEST")


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        pytest.param(b"GIF89a" + b"\x00" * 64, "image/gif", id="gif"),
        pytest.param(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64, "image/heic", id="heic"),
        pytest.param(b"BM" + b"\x00" * 64, "image/bmp", id="bmp"),
    ],
)
def test_unsupported_image_formats(client: TestClient, content: bytes, content_type: str) -> None:
    body = assert_error(
        post_meal(client, ("meal.bin", content, content_type)), 415, "UNSUPPORTED_MEDIA_TYPE"
    )
    assert "unknown format" in body["error"]["details"][0]["issue"]


def test_misleading_content_type_text_claiming_jpeg(client: TestClient) -> None:
    payload = b"<html><script>alert(1)</script></html>"
    assert_error(
        post_meal(client, ("meal.jpg", payload, "image/jpeg")), 415, "UNSUPPORTED_MEDIA_TYPE"
    )


@pytest.mark.parametrize("declared", ["text/plain", "application/octet-stream", "image/gif"])
def test_misleading_content_type_jpeg_claiming_other(
    client: TestClient, jpeg_bytes: bytes, declared: str
) -> None:
    assert_error(
        post_meal(client, ("meal.jpg", jpeg_bytes, declared)), 415, "UNSUPPORTED_MEDIA_TYPE"
    )


def test_type_not_in_configured_allow_list(make_client: ClientFactory, jpeg_bytes: bytes) -> None:
    client = make_client(allowed_image_types="image/png")
    assert_error(
        post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg")), 415, "UNSUPPORTED_MEDIA_TYPE"
    )


# --------------------------------------------------------------------------- IMAGE_TOO_LARGE


def test_oversize_image_rejected_by_chunked_reader(
    make_client: ClientFactory, jpeg_bytes: bytes
) -> None:
    # Body cap (image limit + overhead) is not hit, so the per-image chunked check fires.
    client = make_client(max_image_bytes=len(jpeg_bytes) - 1, multipart_overhead_bytes=65536)
    assert_error(post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg")), 413, "IMAGE_TOO_LARGE")


def test_oversize_request_rejected_by_content_length(
    make_client: ClientFactory, jpeg_bytes: bytes
) -> None:
    client = make_client(max_image_bytes=1024, multipart_overhead_bytes=0)
    assert_error(post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg")), 413, "IMAGE_TOO_LARGE")


def test_oversize_streamed_request_without_content_length(make_client: ClientFactory) -> None:
    client = make_client(max_image_bytes=1024, multipart_overhead_bytes=0)

    def body() -> Iterator[bytes]:
        for _ in range(8):
            yield b"x" * 512

    response = client.post(
        URL, content=body(), headers={"content-type": "multipart/form-data; boundary=abc"}
    )
    assert "content-length" not in {k.lower() for k in response.request.headers}
    assert_error(response, 413, "IMAGE_TOO_LARGE")


# --------------------------------------------------------------------------- IMAGE_UNREADABLE


def test_corrupt_jpeg(client: TestClient) -> None:
    corrupt = b"\xff\xd8\xff\xe0" + b"this is not jpeg data" * 20 + b"\xff\xd9"
    assert_error(post_meal(client, ("meal.jpg", corrupt, "image/jpeg")), 422, "IMAGE_UNREADABLE")


def test_truncated_jpeg(client: TestClient, jpeg_bytes: bytes) -> None:
    truncated = jpeg_bytes[: len(jpeg_bytes) // 2]
    assert_error(post_meal(client, ("meal.jpg", truncated, "image/jpeg")), 422, "IMAGE_UNREADABLE")


def test_jpeg_missing_end_marker(client: TestClient, make_jpeg: Callable[..., bytes]) -> None:
    # OpenCV decodes this silently; the end-of-image check must still reject it.
    data = make_jpeg(640, 480)
    assert data.endswith(b"\xff\xd9")
    assert_error(post_meal(client, ("meal.jpg", data[:-2], "image/jpeg")), 422, "IMAGE_UNREADABLE")


def test_corrupt_png(client: TestClient) -> None:
    corrupt = b"\x89PNG\r\n\x1a\n" + b"garbage" * 20
    assert_error(post_meal(client, ("meal.png", corrupt, "image/png")), 422, "IMAGE_UNREADABLE")


def test_truncated_png(client: TestClient, png_bytes: bytes) -> None:
    truncated = png_bytes[: len(png_bytes) // 2]
    assert_error(post_meal(client, ("meal.png", truncated, "image/png")), 422, "IMAGE_UNREADABLE")


# --------------------------------------------------------------------------- INVALID_METADATA


@pytest.mark.parametrize("meal_type", ["brunch", "Lunch", "LUNCH", "1"])
def test_invalid_meal_type(client: TestClient, jpeg_bytes: bytes, meal_type: str) -> None:
    body = assert_error(
        post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"), meal_type=meal_type),
        422,
        "INVALID_METADATA",
    )
    assert body["error"]["details"][0]["field"] == "meal_type"


@pytest.mark.parametrize(
    "captured_at",
    [
        pytest.param("2026-10-03T12:30:00", id="naive"),
        pytest.param("2026-10-03", id="date-only"),
        pytest.param("1759480200", id="unix-timestamp"),
        pytest.param("not-a-date", id="garbage"),
        pytest.param("2026-13-03T12:30:00Z", id="invalid-month"),
        pytest.param("2026-10-03 12:30:00+05:30", id="space-separator"),
        pytest.param("2026-10-03T12:30:00+0530", id="offset-without-colon"),
        pytest.param("2026-10-03T12:30:00z", id="lowercase-z"),
        pytest.param("2026-10-03T12:05:01Z", id="future-beyond-skew"),
        pytest.param("2999-01-01T00:00:00Z", id="far-future"),
    ],
)
def test_invalid_captured_at(
    fixed_clock_client: TestClient, jpeg_bytes: bytes, captured_at: str
) -> None:
    body = assert_error(
        post_meal(
            fixed_clock_client, ("meal.jpg", jpeg_bytes, "image/jpeg"), captured_at=captured_at
        ),
        422,
        "INVALID_METADATA",
    )
    assert body["error"]["details"][0]["field"] == "captured_at"


def test_reference_object_too_long(make_client: ClientFactory, jpeg_bytes: bytes) -> None:
    client = make_client(reference_object_max_length=5)
    body = assert_error(
        post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"), reference_object="123456"),
        422,
        "INVALID_METADATA",
    )
    assert body["error"]["details"][0]["field"] == "reference_object"


def test_metadata_sent_as_file_part(client: TestClient, jpeg_bytes: bytes) -> None:
    files = {
        "image": ("meal.jpg", jpeg_bytes, "image/jpeg"),
        "meal_type": ("x.txt", b"lunch", "text/plain"),
    }
    assert_error(client.post(URL, files=files), 422, "INVALID_METADATA")


# --------------------------------------------------------------------------- other


def test_unexpected_error_returns_envelope(client: TestClient, jpeg_bytes: bytes) -> None:
    class ExplodingService:
        async def analyze(self, **_: Any) -> None:
            raise RuntimeError("boom")

    client.app.dependency_overrides[get_meal_analysis_service] = ExplodingService  # type: ignore[attr-defined]
    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"))
    body = assert_error(response, 500, "INTERNAL_ERROR")
    assert "boom" not in body["error"]["message"]  # internals are not leaked


def test_get_is_not_allowed(client: TestClient) -> None:
    response = client.get(URL)
    assert_error(response, 405, "METHOD_NOT_ALLOWED")
    assert "POST" in response.headers["allow"]


def test_openapi_documents_contract(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    operation = spec["paths"][URL]["post"]
    assert {"413", "415", "422"} <= set(operation["responses"])

    schema_ref = operation["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    properties = spec["components"]["schemas"][schema_ref.rsplit("/", 1)[-1]]["properties"]
    assert properties["reference_object"]["description"].startswith("EXPERIMENTAL")
    assert properties["meal_type"]["enum"] == ["breakfast", "lunch", "dinner", "snack"]
    assert properties["captured_at"]["format"] == "date-time"


def test_captured_at_window_uses_configured_skew(
    make_client: ClientFactory, jpeg_bytes: bytes
) -> None:
    client = make_client(captured_at_max_future_skew_seconds=0)
    client.app.dependency_overrides[get_clock] = lambda: lambda: FIXED_NOW  # type: ignore[attr-defined]
    one_second_ahead = (FIXED_NOW + timedelta(seconds=1)).isoformat()
    assert_error(
        post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"), captured_at=one_second_ahead),
        422,
        "INVALID_METADATA",
    )


# ----------------------------------------------------- trained recogniser (random-weight fixture)


def test_trained_recognizer_is_used_and_the_rest_stays_flagged_mock(
    make_client: ClientFactory, make_bundle: Callable[..., Any], jpeg_bytes: bytes
) -> None:
    client = make_client(recognizer="torch", model_path=str(make_bundle(threshold=0.0)))

    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"))

    assert response.status_code == 200, response.text
    result = MealAnalysisResponse.model_validate(response.json())
    assert {item.label for item in result.items} == {"kiribath", "lunu_miris", "hoppers"}
    assert {item.food_code for item in result.items} == {"SL_9", None, "SL_37"}
    assert result.meta.model_name == "mobilenet_v3_large-multilabel"
    assert result.meta.model_version == "fixture-random-weights"
    # Portion estimation and nutrition lookup are still mock, and the response says so.
    assert result.meta.is_mock is True
    assert result.meta.warnings == [
        "PARTLY MOCK RESPONSE: synthetic placeholders are used for portion estimation "
        "and nutrition lookup; they are not real data."
    ]
    # No nutrient value is invented for a real food: unknown stays null.
    assert all(item.nutrition_source is None for item in result.items)
    assert result.totals.energy_kcal is None


def test_no_food_above_threshold_gives_an_empty_list_and_a_warning(
    make_client: ClientFactory, make_bundle: Callable[..., Any], jpeg_bytes: bytes
) -> None:
    client = make_client(recognizer="torch", model_path=str(make_bundle(threshold=1.0)))

    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"))

    assert response.status_code == 200, response.text
    result = MealAnalysisResponse.model_validate(response.json())
    assert result.items == []
    assert "No food was recognised in the image." in result.meta.warnings


# ------------------------------------------------------------------ composition table (fixture)


def test_table_lookup_with_the_mock_recognizer_leaves_nutrients_unknown(
    make_client: ClientFactory, make_table: Callable[..., Any], jpeg_bytes: bytes
) -> None:
    client = make_client(nutrition_table_path=str(make_table()))

    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"))

    result = MealAnalysisResponse.model_validate(response.json())
    assert all(item.nutrition_source is None for item in result.items)
    assert result.totals.energy_kcal is None
    assert (
        "No nutrition data for 'mock_item_a': its nutrients, and the meal totals, "
        "are unknown (null)." in result.meta.warnings
    )


def test_table_values_reach_the_response_for_matched_foods(
    make_client: ClientFactory,
    make_bundle: Callable[..., Any],
    make_table: Callable[..., Any],
    jpeg_bytes: bytes,
) -> None:
    client = make_client(
        recognizer="torch",
        model_path=str(make_bundle(classes=("kiribath", "hoppers", "lunu_miris"))),
        nutrition_table_path=str(make_table()),
    )

    response = post_meal(client, ("meal.jpg", jpeg_bytes, "image/jpeg"))

    assert response.status_code == 200, response.text
    result = MealAnalysisResponse.model_validate(response.json())
    items = {item.label: item for item in result.items}
    # Fixture values for SL_9 / SL_37, scaled to the mock 100 g portion.
    assert items["kiribath"].nutrition.carbohydrate_g == pytest.approx(20.0)
    assert items["kiribath"].nutrition.sugars_g is None
    assert items["kiribath"].nutrition_source is not None
    assert items["kiribath"].nutrition_source.source_food_id == "SL_9"
    assert items["hoppers"].nutrition.energy_kcal == pytest.approx(150.0)
    assert items["hoppers"].nutrition.dietary_fiber_g is None  # blank in the table
    assert items["lunu_miris"].nutrition.energy_kcal is None  # no honest match
    assert result.totals.energy_kcal is None  # one unknown makes the total unknown
    assert result.meta.warnings == [
        "PARTLY MOCK RESPONSE: synthetic placeholders are used for portion estimation; "
        "they are not real data.",
        "No nutrition data for 'lunu_miris': its nutrients, and the meal totals, "
        "are unknown (null).",
    ]
