from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from c1_food_nutrition.schemas.meal_analysis import (
    MealAnalysisMetadata,
    MealType,
    MetadataValidationContext,
)

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
CONTEXT = MetadataValidationContext(
    now=NOW, max_future_skew=timedelta(seconds=300), reference_object_max_length=10
)


def validate(**data: object) -> MealAnalysisMetadata:
    return MealAnalysisMetadata.model_validate(data, context=CONTEXT)


def test_all_fields_optional() -> None:
    metadata = validate()
    assert metadata == MealAnalysisMetadata()


def test_captured_at_normalised_to_utc() -> None:
    metadata = validate(captured_at="2026-10-03T05:30:00+05:30")
    assert metadata.captured_at == datetime(2026, 10, 3, 0, 0, tzinfo=UTC)
    assert metadata.captured_at is not None
    assert metadata.captured_at.utcoffset() == timedelta(0)


def test_aware_datetime_object_accepted() -> None:
    value = datetime(2026, 10, 3, 9, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert validate(captured_at=value).captured_at == datetime(2026, 10, 3, 3, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 10, 3, 9, 0),  # noqa: DTZ001 - naive on purpose
        1759480200,
        1759480200.0,
        "2026-10-03T09:00:00",
        "2026-10-03T25:00:00Z",
        "2026-10-03T09:00:00+24:00",
    ],
)
def test_captured_at_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        validate(captured_at=value)


def test_future_skew_boundary() -> None:
    assert validate(captured_at="2026-10-03T12:05:00Z").captured_at is not None
    with pytest.raises(ValidationError, match="future"):
        validate(captured_at="2026-10-03T12:05:01Z")


def test_without_context_only_format_rules_apply() -> None:
    metadata = MealAnalysisMetadata.model_validate(
        {"captured_at": "2999-01-01T00:00:00Z", "reference_object": "x" * 1000}
    )
    assert metadata.captured_at is not None


def test_reference_object_length_limit_and_passthrough() -> None:
    assert validate(reference_object=" coin  ").reference_object == " coin  "
    with pytest.raises(ValidationError):
        validate(reference_object="x" * 11)


def test_meal_type_values() -> None:
    assert [m.value for m in MealType] == ["breakfast", "lunch", "dinner", "snack"]
    with pytest.raises(ValidationError):
        validate(meal_type="brunch")


def test_unknown_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        validate(portion_hint="large")
