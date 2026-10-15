"""Application configuration loaded from environment variables (and an optional ``.env``)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, NonNegativeInt, PositiveInt, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

#: Image media types the service can detect from file content and decode with OpenCV.
#: ``ALLOWED_IMAGE_TYPES`` may narrow this set but never widen it (ADR 0004).
SUPPORTED_IMAGE_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png"})


class Settings(BaseSettings):
    """C1 service settings.

    Every field maps to an upper-case environment variable of the same name
    (for example ``max_image_bytes`` reads ``MAX_IMAGE_BYTES``). See ``.env.example``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "c1-food-nutrition"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: str = "sqlite:///./c1_local.db"

    allowed_image_types: Annotated[frozenset[str], NoDecode] = Field(
        default=SUPPORTED_IMAGE_TYPES,
        description="Comma-separated MIME types accepted for meal images.",
    )
    max_image_bytes: PositiveInt = Field(
        default=10 * 1024 * 1024,
        description="Maximum accepted image size in bytes.",
    )
    upload_chunk_bytes: PositiveInt = Field(
        default=64 * 1024,
        description="Chunk size used when reading uploads.",
    )
    multipart_overhead_bytes: NonNegativeInt = Field(
        default=64 * 1024,
        description=(
            "Allowance for multipart boundaries and metadata fields on top of "
            "MAX_IMAGE_BYTES when capping the whole request body."
        ),
    )
    captured_at_max_future_skew_seconds: NonNegativeInt = Field(
        default=300,
        description="How far in the future captured_at may be, to tolerate client clock skew.",
    )
    reference_object_max_length: PositiveInt = Field(
        default=200,
        description="Maximum length of the experimental reference_object field.",
    )

    recognizer: Literal["mock", "torch"] = Field(
        default="mock",
        description="Food recogniser: 'mock' (synthetic) or 'torch' (trained model).",
    )
    model_path: Path | None = Field(
        default=None,
        description="Model bundle file; required when RECOGNIZER=torch. Never committed to git.",
    )
    nutrition_table_path: Path | None = Field(
        default=None,
        description=(
            "Combined food-composition CSV (data/c1/c1_foods_combined.csv). Without it the "
            "nutrition lookup is the mock. Never committed to git."
        ),
    )
    model_device: Literal["cpu", "cuda"] = Field(
        default="cpu", description="Device the trained model runs on."
    )

    @model_validator(mode="after")
    def _check_recognizer(self) -> "Settings":
        """A trained recogniser needs a model file."""
        if self.recognizer == "torch" and self.model_path is None:
            raise ValueError("MODEL_PATH is required when RECOGNIZER=torch")
        return self

    @field_validator("allowed_image_types", mode="before")
    @classmethod
    def _parse_allowed_image_types(cls, value: object) -> object:
        """Accept a comma-separated string as well as an iterable of MIME types."""
        if isinstance(value, str):
            value = value.split(",")
        if isinstance(value, list | tuple | set | frozenset):
            return frozenset(str(item).strip().lower() for item in value if str(item).strip())
        return value

    @field_validator("allowed_image_types")
    @classmethod
    def _check_allowed_image_types(cls, value: frozenset[str]) -> frozenset[str]:
        """Reject empty configuration and types the service cannot validate or decode."""
        if not value:
            raise ValueError("ALLOWED_IMAGE_TYPES must contain at least one type")
        unsupported = value - SUPPORTED_IMAGE_TYPES
        if unsupported:
            raise ValueError(
                f"Unsupported image types {sorted(unsupported)}; "
                f"supported types are {sorted(SUPPORTED_IMAGE_TYPES)}"
            )
        return value

    @property
    def max_request_bytes(self) -> int:
        """Upper bound for the whole request body (image plus multipart overhead)."""
        return self.max_image_bytes + self.multipart_overhead_bytes


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance (cached)."""
    return Settings()
