"""Nutrition calculation tests. All profiles here are TEST FIXTURES, not real food data."""

import pytest

from c1_food_nutrition.schemas.nutrition import (
    NUTRIENT_FIELDS,
    NutrientProfile,
    NutritionSourceCode,
)
from c1_food_nutrition.services.nutrition import (
    PlaceholderNutritionLookup,
    scale_profile,
    sum_profiles,
)

FIXTURE_PROFILE = NutrientProfile(energy_kcal=200.0, carbohydrate_g=40.0, protein_g=None)


def test_scale_profile() -> None:
    scaled = scale_profile(FIXTURE_PROFILE, grams=150)
    assert scaled.energy_kcal == pytest.approx(300.0)
    assert scaled.carbohydrate_g == pytest.approx(60.0)
    assert scaled.protein_g is None  # unknown stays unknown


def test_scale_profile_rejects_negative_grams() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        scale_profile(FIXTURE_PROFILE, grams=-1)


def test_sum_profiles_marks_unknown_totals_as_none() -> None:
    other = NutrientProfile(energy_kcal=50.0, carbohydrate_g=5.0, protein_g=2.0)
    total = sum_profiles([FIXTURE_PROFILE, other])
    assert total.energy_kcal == pytest.approx(250.0)
    assert total.carbohydrate_g == pytest.approx(45.0)
    assert total.protein_g is None  # unknown for one item -> unknown total


def test_sum_profiles_empty() -> None:
    assert sum_profiles([]) == NutrientProfile()


def test_nutrient_fields_are_stable() -> None:
    assert NUTRIENT_FIELDS == (
        "energy_kcal",
        "carbohydrate_g",
        "sugars_g",
        "dietary_fiber_g",
        "protein_g",
        "fat_g",
        "sodium_mg",
    )


def test_placeholder_lookup_only_serves_mock_codes() -> None:
    lookup = PlaceholderNutritionLookup()
    assert lookup.is_mock is True
    assert lookup.per_100g("REAL-123") is None
    result = lookup.per_100g("MOCK-0001")
    assert result is not None
    assert result[1].source is NutritionSourceCode.MOCK
