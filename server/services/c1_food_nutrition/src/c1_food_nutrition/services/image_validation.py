"""Validation of uploaded meal images (ADR 0004).

Order of checks:
1. read in chunks, aborting once ``max_bytes`` is exceeded  -> IMAGE_TOO_LARGE (413)
2. empty upload                                             -> IMAGE_REQUIRED (422)
3. content (magic bytes) must be an allowed format          -> UNSUPPORTED_MEDIA_TYPE (415)
4. declared Content-Type must also be an allowed type       -> UNSUPPORTED_MEDIA_TYPE (415)
5. bytes must decode with ``cv2.imdecode`` (not truncated)  -> IMAGE_UNREADABLE (422)
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from c1_food_nutrition.config import Settings
from c1_food_nutrition.core.errors import (
    ErrorDetailItem,
    ImageRequiredError,
    ImageTooLargeError,
    ImageUnreadableError,
    UnsupportedMediaTypeError,
)
from c1_food_nutrition.ml.interfaces import BgrImage
from c1_food_nutrition.ml.preprocessing import decode_image

logger = logging.getLogger(__name__)

_JPEG_SIGNATURE = b"\xff\xd8\xff"
_JPEG_EOI = b"\xff\xd9"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Non-standard spellings some clients send for JPEG.
_MEDIA_TYPE_ALIASES: dict[str, str] = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}


class AsyncReadable(Protocol):
    """Minimal async file interface (satisfied by FastAPI's ``UploadFile``)."""

    async def read(self, size: int = -1) -> bytes:
        """Read up to ``size`` bytes; an empty result means end of file."""
        ...


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    """An accepted, decoded image."""

    pixels: BgrImage
    media_type: str
    width: int
    height: int
    size_bytes: int


def detect_image_type(data: bytes) -> str | None:
    """Identify the image format from its leading bytes (no Pillow, no imghdr)."""
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    return None


def normalize_media_type(content_type: str | None) -> str | None:
    """Lower-case a Content-Type, drop parameters and map known aliases."""
    if not content_type:
        return None
    media_type = content_type.split(";", 1)[0].strip().lower()
    return _MEDIA_TYPE_ALIASES.get(media_type, media_type) or None


def _is_truncated(data: bytes, media_type: str) -> bool:
    """Detect truncation that ``cv2.imdecode`` may silently tolerate.

    libjpeg decodes truncated JPEGs into a partially grey image without failing, so a
    JPEG must contain an End-Of-Image marker after its signature. (0xFFD9 cannot occur
    inside entropy-coded data because of byte stuffing.)
    """
    if media_type == "image/jpeg":
        return data.find(_JPEG_EOI, len(_JPEG_SIGNATURE)) == -1
    return False


class ImageValidator:
    """Applies the upload rules configured through ``Settings``."""

    def __init__(self, *, allowed_types: Iterable[str], max_bytes: int, chunk_bytes: int) -> None:
        self._allowed_types = frozenset(allowed_types)
        self._max_bytes = max_bytes
        self._chunk_bytes = chunk_bytes

    @classmethod
    def from_settings(cls, settings: Settings) -> "ImageValidator":
        """Build a validator from application settings."""
        return cls(
            allowed_types=settings.allowed_image_types,
            max_bytes=settings.max_image_bytes,
            chunk_bytes=settings.upload_chunk_bytes,
        )

    async def read_limited(self, source: AsyncReadable) -> bytes:
        """Read ``source`` chunk by chunk, stopping as soon as the size limit is exceeded."""
        buffer = bytearray()
        while chunk := await source.read(self._chunk_bytes):
            buffer.extend(chunk)
            if len(buffer) > self._max_bytes:
                raise ImageTooLargeError(
                    f"Image exceeds the maximum allowed size of {self._max_bytes} bytes.",
                    [ErrorDetailItem(field="image", issue=f"max {self._max_bytes} bytes")],
                )
        return bytes(buffer)

    def validate_bytes(self, data: bytes, declared_content_type: str | None) -> ValidatedImage:
        """Check format, declared type and decodability of already-read image bytes."""
        if not data:
            raise ImageRequiredError(
                "The uploaded image file is empty.",
                [ErrorDetailItem(field="image", issue="file has no content")],
            )

        allowed = sorted(self._allowed_types)
        detected = detect_image_type(data)
        if detected is None or detected not in self._allowed_types:
            raise UnsupportedMediaTypeError(
                "The uploaded file is not a supported image format.",
                [
                    ErrorDetailItem(
                        field="image",
                        issue=f"detected {detected or 'unknown format'}; allowed: {allowed}",
                    )
                ],
            )

        declared = normalize_media_type(declared_content_type)
        if declared not in self._allowed_types:
            raise UnsupportedMediaTypeError(
                "The image part's Content-Type is missing or not an allowed image type.",
                [
                    ErrorDetailItem(
                        field="image",
                        issue=f"declared Content-Type {declared_content_type!r}; "
                        f"allowed: {allowed}",
                    )
                ],
            )
        if declared != detected:
            logger.warning(
                "declared image type differs from detected content",
                extra={"declared_type": declared, "detected_type": detected},
            )

        pixels = None if _is_truncated(data, detected) else decode_image(data)
        if pixels is None:
            raise ImageUnreadableError(
                "The image could not be decoded; it may be corrupt or truncated.",
                [ErrorDetailItem(field="image", issue=f"invalid {detected} data")],
            )

        height, width = pixels.shape[:2]
        return ValidatedImage(
            pixels=pixels,
            media_type=detected,
            width=int(width),
            height=int(height),
            size_bytes=len(data),
        )

    async def validate(
        self, source: AsyncReadable, declared_content_type: str | None
    ) -> ValidatedImage:
        """Read and fully validate an uploaded image."""
        data = await self.read_limited(source)
        return self.validate_bytes(data, declared_content_type)
