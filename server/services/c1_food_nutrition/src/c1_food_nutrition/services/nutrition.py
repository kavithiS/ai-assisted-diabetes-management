"""Nutrition calculation: scale per-100 g composition data to a portion and sum a meal."""

from collections.abc import Iterable
from typing import Protocol

from c1_food_nutrition.schemas.nutrition import (
    NUTRIENT_FIELDS,
    NutrientProfile,
    NutritionSourceCode,
    NutritionSourceRef,
)


class NutritionLookup(Protocol):
    """Provides per-100 g nutrient profiles for food codes."""

    @property
    def is_mock(self) -> bool:
        """True if this lookup returns synthetic placeholder values."""
        ...

    def per_100g(self, food_code: str) -> tuple[NutrientProfile, NutritionSourceRef] | None:
        """Return the per-100 g profile and its source, or ``None`` if unknown."""
        ...


def scale_profile(per_100g: NutrientProfile, grams: float) -> NutrientProfile:
    """Scale a per-100 g profile to ``grams``; unknown (``None``) values stay unknown."""
    if grams < 0:
        raise ValueError("grams must be non-negative")
    factor = grams / 100.0
    values = per_100g.model_dump()
    return NutrientProfile(
        **{
            name: None if values[name] is None else values[name] * factor
            for name in NUTRIENT_FIELDS
        }
    )


def sum_profiles(profiles: Iterable[NutrientProfile]) -> NutrientProfile:
    """Sum profiles nutrient by nutrient.

    A nutrient total is ``None`` if it is unknown for any item, so missing data is never
    hidden by a partial sum. An empty input yields all-``None``.
    """
    dumped = [profile.model_dump() for profile in profiles]
    if not dumped:
        return NutrientProfile()
    totals: dict[str, float | None] = {}
    for name in NUTRIENT_FIELDS:
        values = [item[name] for item in dumped]
        totals[name] = None if any(v is None for v in values) else float(sum(values))
    return NutrientProfile(**totals)


class PlaceholderNutritionLookup:
    """MOCK nutrition lookup for Phase 0.

    The values below are SYNTHETIC PLACEHOLDERS chosen to be round and obviously fake.
    They are NOT taken from, and must not be mistaken for, the MRI Sri Lanka FCDB or
    USDA FoodData Central.
    """

    _PLACEHOLDER_PER_100G = NutrientProfile(
        energy_kcal=100.0,
        carbohydrate_g=10.0,
        sugars_g=1.0,
        dietary_fiber_g=1.0,
        protein_g=1.0,
        fat_g=1.0,
        sodium_mg=10.0,
    )

    @property
    def is_mock(self) -> bool:
        """Always true."""
        return True

    def per_100g(self, food_code: str) -> tuple[NutrientProfile, NutritionSourceRef] | None:
        """Return the placeholder profile for mock food codes only."""
        if not food_code.startswith("MOCK-"):
            return None
        return self._PLACEHOLDER_PER_100G, NutritionSourceRef(
            source=NutritionSourceCode.MOCK, source_food_id=food_code
        )
