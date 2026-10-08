from collections.abc import Callable

import pytest
from pydantic import ValidationError

from c1_food_nutrition.config import SUPPORTED_IMAGE_TYPES, Settings

SettingsFactory = Callable[..., Settings]


def test_defaults(make_settings: SettingsFactory) -> None:
    settings = make_settings()
    assert settings.allowed_image_types == SUPPORTED_IMAGE_TYPES
    assert (
        settings.max_request_bytes == settings.max_image_bytes + settings.multipart_overhead_bytes
    )


def test_allowed_types_parsed_from_comma_separated_string(make_settings: SettingsFactory) -> None:
    settings = make_settings(allowed_image_types=" IMAGE/PNG , image/jpeg ,")
    assert settings.allowed_image_types == frozenset({"image/png", "image/jpeg"})


def test_allowed_types_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_IMAGE_TYPES", "image/png")
    monkeypatch.setenv("MAX_IMAGE_BYTES", "2048")
    settings = Settings(_env_file=None)
    assert settings.allowed_image_types == frozenset({"image/png"})
    assert settings.max_image_bytes == 2048


@pytest.mark.parametrize("value", ["image/heic", "image/jpeg,image/gif", "", " , "])
def test_unsupported_or_empty_types_rejected(make_settings: SettingsFactory, value: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(allowed_image_types=value)


@pytest.mark.parametrize("field", ["max_image_bytes", "upload_chunk_bytes"])
def test_sizes_must_be_positive(make_settings: SettingsFactory, field: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(**{field: 0})
