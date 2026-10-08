import pytest

from c1_food_nutrition.core.errors import (
    ImageRequiredError,
    ImageTooLargeError,
    ImageUnreadableError,
    UnsupportedMediaTypeError,
)
from c1_food_nutrition.services.image_validation import (
    ImageValidator,
    detect_image_type,
    normalize_media_type,
)

pytestmark = pytest.mark.anyio


class CountingReader:
    """Fake upload that serves ``total`` bytes and records how much was read."""

    def __init__(self, total: int) -> None:
        self.remaining = total
        self.bytes_read = 0
        self.calls = 0

    async def read(self, size: int = -1) -> bytes:
        self.calls += 1
        n = self.remaining if size < 0 else min(size, self.remaining)
        self.remaining -= n
        self.bytes_read += n
        return b"\xff" * n


def make_validator(max_bytes: int = 1000, chunk_bytes: int = 100) -> ImageValidator:
    return ImageValidator(
        allowed_types={"image/jpeg", "image/png"}, max_bytes=max_bytes, chunk_bytes=chunk_bytes
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"\xff\xd8\xff\xe0rest", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\nrest", "image/png"),
        (b"GIF89a", None),
        (b"\xff\xd8", None),  # too short to be a JPEG signature
        (b"", None),
    ],
)
def test_detect_image_type(data: bytes, expected: str | None) -> None:
    assert detect_image_type(data) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("image/JPEG", "image/jpeg"),
        ("image/jpeg; charset=binary", "image/jpeg"),
        ("image/jpg", "image/jpeg"),
        ("image/pjpeg", "image/jpeg"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_media_type(value: str | None, expected: str | None) -> None:
    assert normalize_media_type(value) == expected


async def test_read_limited_returns_all_bytes_under_limit() -> None:
    reader = CountingReader(total=1000)
    data = await make_validator(max_bytes=1000).read_limited(reader)
    assert len(data) == 1000


async def test_read_limited_stops_early_when_limit_exceeded() -> None:
    reader = CountingReader(total=10_000_000)
    with pytest.raises(ImageTooLargeError):
        await make_validator(max_bytes=1000, chunk_bytes=100).read_limited(reader)
    # Never reads more than one chunk past the limit, regardless of the file size.
    assert reader.bytes_read <= 1000 + 100
    assert reader.calls <= 11


def test_validate_bytes_order_of_checks(jpeg_bytes: bytes) -> None:
    validator = make_validator(max_bytes=10_000_000)
    with pytest.raises(ImageRequiredError):
        validator.validate_bytes(b"", "image/jpeg")
    with pytest.raises(UnsupportedMediaTypeError):
        validator.validate_bytes(b"plain text", "image/jpeg")
    with pytest.raises(UnsupportedMediaTypeError):
        validator.validate_bytes(jpeg_bytes, None)
    with pytest.raises(ImageUnreadableError):
        validator.validate_bytes(b"\xff\xd8\xff\xe0garbage\xff\xd9", "image/jpeg")


def test_validate_bytes_success(png_bytes: bytes) -> None:
    result = make_validator(max_bytes=10_000_000).validate_bytes(png_bytes, "image/png")
    assert (result.width, result.height, result.media_type) == (64, 48, "image/png")
    assert result.pixels.shape == (48, 64, 3)
