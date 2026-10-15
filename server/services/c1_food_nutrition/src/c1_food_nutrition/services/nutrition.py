"""Nutrition calculation: scale per-100 g composition data to a portion and sum a meal."""

import csv
import math
from collections.abc import Iterable
from pathlib import Path
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


#: Columns the composition table must have. A header such as ``food_100me`` (a corrupted export
#: in which every "na" became "100") fails this check, so a corrupted file can never load.
REQUIRED_COLUMNS = (
    "food_id",
    "food_name",
    "source",
    "energy_kcal",
    "carbohydrate_g",
    "fat_g",
    "protein_g",
    "fibre_g",
    "sodium_mg",
)

#: Table sources that may be used, and the contract value recorded for each. Other sources in
#: the combined table (regional tables) are skipped until the supervisors agree to use them and
#: the ``nutrition_source`` enum is extended (``docs/OPEN_ITEMS.md`` A1).
ALLOWED_SOURCES: dict[str, NutritionSourceCode] = {
    "Sri Lankan Food Composition Database": NutritionSourceCode.MRI_SL_FCDB,
    "USDA FoodData Central, Foundation Foods": NutritionSourceCode.USDA_FDC,
}

#: Contract field -> table column. ``sugars_g`` has no column, so it is always unknown.
#: ``carbohydrate_g`` in the table is AVAILABLE carbohydrate (fibre excluded).
COLUMN_FOR_FIELD = {
    "energy_kcal": "energy_kcal",
    "carbohydrate_g": "carbohydrate_g",
    "dietary_fiber_g": "fibre_g",
    "protein_g": "protein_g",
    "fat_g": "fat_g",
    "sodium_mg": "sodium_mg",
}


class CompositionTableError(ValueError):
    """The composition table is unreadable, has the wrong header or holds a bad value."""


class CompositionTableLookup:
    """Per-100 g nutrient profiles read from the combined food-composition CSV.

    Only foods from :data:`ALLOWED_SOURCES` are loaded. A blank cell is unknown (``None``),
    never zero. The lookup key is the table's ``food_id`` (for example ``SL_9``).
    """

    def __init__(
        self, entries: dict[str, tuple[NutrientProfile, NutritionSourceRef, str]], skipped: int = 0
    ) -> None:
        self._entries = entries
        self.skipped_rows = skipped

    @classmethod
    def from_csv(cls, path: Path) -> "CompositionTableLookup":
        """Load ``path``; a problem raises :class:`CompositionTableError` naming file and row."""
        entries: dict[str, tuple[NutrientProfile, NutritionSourceRef, str]] = {}
        skipped = 0
        try:
            handle = path.open(encoding="utf-8", newline="")
        except OSError as exc:
            raise CompositionTableError(f"cannot read {path}: {exc}") from exc
        with handle:
            reader = csv.DictReader(handle)
            missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise CompositionTableError(f"{path}: header lacks columns {missing}")
            for number, row in enumerate(reader, start=2):
                source = ALLOWED_SOURCES.get(row["source"])
                if source is None:
                    skipped += 1
                    continue
                food_id = row["food_id"].strip()
                if not food_id or food_id in entries:
                    raise CompositionTableError(f"{path}, row {number}: empty or repeated food_id")
                values: dict[str, float | None] = {}
                for name, column in COLUMN_FOR_FIELD.items():
                    values[name] = _number(row[column], path, number, column)
                entries[food_id] = (
                    NutrientProfile(**values),
                    NutritionSourceRef(source=source, source_food_id=food_id),
                    row["food_name"].strip(),
                )
        if not entries:
            raise CompositionTableError(f"{path}: no rows from an allowed source")
        return cls(entries, skipped)

    @property
    def is_mock(self) -> bool:
        """Always false: the values come from the composition table."""
        return False

    def __len__(self) -> int:
        return len(self._entries)

    def food_name(self, food_code: str) -> str | None:
        """Name of the table entry, or ``None`` if the code is unknown."""
        entry = self._entries.get(food_code)
        return entry[2] if entry else None

    def per_100g(self, food_code: str) -> tuple[NutrientProfile, NutritionSourceRef] | None:
        """The profile and source for a table ``food_id``; ``None`` for an unknown code."""
        entry = self._entries.get(food_code)
        return (entry[0], entry[1]) if entry else None


def _number(text: str, path: Path, row: int, column: str) -> float | None:
    """A non-negative number, or ``None`` for a blank cell."""
    text = text.strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        raise CompositionTableError(
            f"{path}, row {row}: {column} is not a number: {text!r}"
        ) from None
    if not math.isfinite(value) or value < 0:
        raise CompositionTableError(f"{path}, row {row}: {column} must be 0 or more, got {text!r}")
    return value
