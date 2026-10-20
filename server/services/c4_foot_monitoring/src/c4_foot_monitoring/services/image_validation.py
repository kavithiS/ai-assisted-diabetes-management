"""Validation of uploaded foot images (same rules as C1's meal images).

Order of checks:
1. read in chunks, aborting once ``max_bytes`` is exceeded  -> IMAGE_TOO_LARGE (413)
2. empty upload                                             -> IMAGE_REQUIRED (422)
3. content (magic bytes) must be an allowed format          -> UNSUPPORTED_MEDIA_TYPE (415)
4. declared Content-Type must also be an allowed type       -> UNSUPPORTED_MEDIA_TYPE (415)
5. bytes must decode with OpenCV (and a JPEG must not be truncated) -> IMAGE_UNREADABLE (422)

The image is kept in memory only for the request. It is never written to disk or the database.
"""

from collections.abc import Iterable
from typing import Protocol

from c4_foot_monitoring.config import Settings
from c4_foot_monitoring.core.errors import (
    ErrorDetailItem,
    ImageRequiredError,
    ImageTooLargeError,
    ImageUnreadableError,
    UnsupportedMediaTypeError,
)
from c4_foot_monitoring.ml.interfaces import BgrImage
from c4_foot_monitoring.ml.preprocessing import decode_image

_JPEG_SIGNATURE = b"\xff\xd8\xff"
_JPEG_EOI = b"\xff\xd9"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Non-standard spellings some clients send for JPEG.
_MEDIA_TYPE_ALIASES: dict[str, str] = {"image/jpg": "image/jpeg", "image/pjpeg": "image/jpeg"}


class AsyncReadable(Protocol):
    """Minimal async file interface (satisfied by FastAPI's ``UploadFile``)."""

    async def read(self, size: int = -1) -> bytes: ...


def detect_image_type(data: bytes) -> str | None:
    """Identify the image format from its leading bytes."""
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


class ImageValidator:
    """Applies the upload rules configured through ``Settings``."""

    def __init__(self, *, allowed_types: Iterable[str], max_bytes: int, chunk_bytes: int) -> None:
        self._allowed_types = frozenset(allowed_types)
        self._max_bytes = max_bytes
        self._chunk_bytes = chunk_bytes

    @classmethod
    def from_settings(cls, settings: Settings) -> "ImageValidator":
        return cls(
            allowed_types=settings.allowed_image_types,
            max_bytes=settings.max_image_bytes,
            chunk_bytes=settings.upload_chunk_bytes,
        )

    async def validate(self, source: AsyncReadable, declared_content_type: str | None) -> BgrImage:
        """Read, check and decode the upload."""
        data = await self._read_limited(source)
        if not data:
            raise ImageRequiredError(
                "A foot image is required.", [ErrorDetailItem(field="image", issue="empty")]
            )

        detected = detect_image_type(data)
        declared = normalize_media_type(declared_content_type)
        allowed = ", ".join(sorted(self._allowed_types))
        if detected is None or detected not in self._allowed_types:
            raise UnsupportedMediaTypeError(
                "The image must be a JPEG or PNG photo.",
                [ErrorDetailItem(field="image", issue=f"allowed: {allowed}")],
            )
        if declared is not None and declared not in self._allowed_types:
            raise UnsupportedMediaTypeError(
                "The image must be a JPEG or PNG photo.",
                [ErrorDetailItem(field="image", issue=f"declared type {declared} not allowed")],
            )

        truncated = detected == "image/jpeg" and data.find(_JPEG_EOI, len(_JPEG_SIGNATURE)) == -1
        image = None if truncated else decode_image(data)
        if image is None:
            raise ImageUnreadableError(
                "The image could not be read.",
                [ErrorDetailItem(field="image", issue="not a readable image")],
            )
        return image

    async def _read_limited(self, source: AsyncReadable) -> bytes:
        """Read chunk by chunk, stopping as soon as the size limit is exceeded."""
        buffer = bytearray()
        while chunk := await source.read(self._chunk_bytes):
            buffer.extend(chunk)
            if len(buffer) > self._max_bytes:
                raise ImageTooLargeError(
                    f"The image is larger than {self._max_bytes} bytes.",
                    [ErrorDetailItem(field="image", issue=f"max {self._max_bytes} bytes")],
                )
        return bytes(buffer)
