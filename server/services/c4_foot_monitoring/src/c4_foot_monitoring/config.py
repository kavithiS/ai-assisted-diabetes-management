"""C4 service settings, loaded from environment variables (and an optional ``.env``).

Every service reads the same root ``.env``, so C4-specific settings start with ``FOOT_``
(for example ``FOOT_MODEL_PATH``). C1 already uses ``MODEL_PATH`` for its own model.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PositiveInt, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Labels the foot classifier can return.
FootLabel = Literal["normal", "ulcer"]

#: Image media types the service can detect from file content and decode with OpenCV.
SUPPORTED_IMAGE_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png"})


class Settings(BaseSettings):
    """C4 service settings. Each field reads the upper-case environment variable of its name."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = "postgresql://diacare:change-me@localhost:5432/diacare"

    foot_model_path: Path | None = Field(
        default=None,
        description=(
            "Trained ResNet50 weights (e.g. data/c4/best_resnet50_dfu.pth). Empty means the "
            "mock classifier. Never committed to git."
        ),
    )
    foot_model_device: Literal["cpu", "cuda"] = Field(
        default="cpu", description="Device the trained model runs on."
    )
    foot_model_classes: tuple[FootLabel, FootLabel] | None = Field(
        default=None,
        description=(
            "Label of each model output index, in training order, as JSON, e.g. "
            '\'["ulcer", "normal"]\'. Required with FOOT_MODEL_PATH. It must match the '
            "class order used in training: [INFORMATION REQUIRED]."
        ),
    )
    foot_low_risk_min_normal_probability: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description=(
            "A 'normal' result at or above this model score is shown as Low, below it as "
            "Medium. Placeholder value; the cut-off is to be agreed with the supervisors "
            "[INFORMATION REQUIRED]."
        ),
    )

    allowed_image_types: frozenset[str] = Field(
        default=SUPPORTED_IMAGE_TYPES, description="MIME types accepted for foot images."
    )
    max_image_bytes: PositiveInt = Field(
        default=10 * 1024 * 1024, description="Maximum accepted image size in bytes."
    )
    upload_chunk_bytes: PositiveInt = Field(
        default=64 * 1024, description="Chunk size used when reading uploads."
    )

    @model_validator(mode="after")
    def _check_model_settings(self) -> "Settings":
        """A trained model needs its class order; image types must be ones we can decode."""
        if self.foot_model_path is not None and self.foot_model_classes is None:
            raise ValueError("FOOT_MODEL_CLASSES is required when FOOT_MODEL_PATH is set")
        if self.foot_model_classes is not None and len(set(self.foot_model_classes)) != 2:
            raise ValueError("FOOT_MODEL_CLASSES must name 'normal' and 'ulcer' once each")
        unsupported = self.allowed_image_types - SUPPORTED_IMAGE_TYPES
        if not self.allowed_image_types or unsupported:
            allowed = sorted(SUPPORTED_IMAGE_TYPES)
            raise ValueError(f"ALLOWED_IMAGE_TYPES must be a non-empty subset of {allowed}")
        return self


@lru_cache
def get_settings() -> Settings:
    """Settings from the environment, read once."""
    return Settings()
