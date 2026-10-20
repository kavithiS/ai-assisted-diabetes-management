"""The owner's food matches (2026-10-18 and 2026-10-20) and what a plate with them returns."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from c1_food_nutrition.ml.interfaces import BgrImage, PortionEstimate, RecognizedFood
from c1_food_nutrition.ml.labels import load_class_foods
from c1_food_nutrition.schemas.meal_analysis import MealAnalysisMetadata
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode
from c1_food_nutrition.services.image_validation import ImageValidator
from c1_food_nutrition.services.nutrition import CompositionTableLookup
from c1_food_nutrition.services.pipeline import NO_NUTRITION_WARNING, MealAnalysisService

pytestmark = pytest.mark.anyio

TableFactory = Callable[..., Path]
REAL_TABLE = Path(__file__).parents[5] / "data" / "c1" / "c1_foods_combined.csv"

# class -> (table food_id, match), chosen by the owner on 2026-10-18
# (brinjal_dish and pappadam: 2026-10-20)
OWNER_MATCHES = {
    "dhal_curry": ("SL_54", "exact"),
    "fish_curry": ("SL_146", "close"),
    "meat_curry": ("SL_158", "close"),
    "noodles": ("SL_33", "partial"),
    "milkshake": ("US_170884", "close"),
    "submarine": ("US_170309", "partial"),
    "patty": ("US_167660", "partial"),
    "brinjal_dish": ("SL_72", "close"),
    "pappadam": ("US_168106", "partial"),
}
# no honest match in the allowed tables: nutrients stay unknown
STAY_UNKNOWN = (
    "asmi",
    "cutlet",
    "kokis",
    "konda_kewum",
    "lunu_miris",
    "mun_kewum",
    "shrimp_curry",
    "watalappam",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class ClassRecognizer:
    """Returns the given classes the way the trained recogniser would (food_code from the map)."""

    model_name = "fixture"
    model_version = "1"
    is_mock = False

    def __init__(self, classes: list[str]) -> None:
        foods = load_class_foods()
        self._items = [RecognizedFood(c, 0.9, food_code=foods[c].food_id) for c in classes]

    def recognize(self, image: BgrImage) -> list[RecognizedFood]:
        return list(self._items)


class HundredGrams:
    is_mock = False

    def estimate(
        self, image: BgrImage, food: RecognizedFood, reference_object: str | None
    ) -> PortionEstimate:
        return PortionEstimate(grams=100.0, method="model", confidence=None)


class BytesReader:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def read(self, size: int = -1) -> bytes:
        chunk, self._data = (
            (self._data, b"") if size < 0 else (self._data[:size], self._data[size:])
        )
        return chunk


def test_owner_matches_are_recorded() -> None:
    table = load_class_foods()
    for name, (food_id, match) in OWNER_MATCHES.items():
        assert (table[name].food_id, table[name].match) == (food_id, match), name
        assert "owner choice 2026-10-" in table[name].note, name
    for name in STAY_UNKNOWN:
        assert table[name].food_id is None and table[name].match == "none", name
    assert "SL_32" not in {e.food_id for e in table.values()}


def test_usda_sr_legacy_rows_are_allowed(make_table: TableFactory) -> None:
    row = 'US_7,Fixture SR Legacy Food,x,,50,5,0.5,1,0.5,5,"USDA FoodData Central, SR Legacy",'
    found = CompositionTableLookup.from_csv(make_table(rows=(row,))).per_100g("US_7")
    assert found is not None and found[1].source is NutritionSourceCode.USDA_FDC


async def analyze(classes: list[str], jpeg_bytes: bytes, lookup: CompositionTableLookup):  # type: ignore[no-untyped-def]
    service = MealAnalysisService(
        image_validator=ImageValidator(
            allowed_types={"image/jpeg"}, max_bytes=1_000_000, chunk_bytes=1024
        ),
        recognizer=ClassRecognizer(classes),
        portion_estimator=HundredGrams(),
        nutrition_lookup=lookup,
        clock=lambda: datetime(2026, 10, 18, tzinfo=UTC),
    )
    return await service.analyze(
        image=BytesReader(jpeg_bytes),
        declared_content_type="image/jpeg",
        metadata=MealAnalysisMetadata(),
    )


@pytest.mark.skipif(not REAL_TABLE.is_file(), reason="the (gitignored) combined table is absent")
async def test_plate_with_every_new_match_has_known_totals(jpeg_bytes: bytes) -> None:
    lookup = CompositionTableLookup.from_csv(REAL_TABLE)
    for name in OWNER_MATCHES:  # each food alone
        result = await analyze([name], jpeg_bytes, lookup)
        item = result.items[0]
        assert item.nutrition_source is not None, name
        for field in ("energy_kcal", "carbohydrate_g", "protein_g", "fat_g", "sodium_mg"):
            assert getattr(item.nutrition, field) is not None, f"{name}.{field}"
        assert item.nutrition.sugars_g is None, name  # the table has no sugars column
        assert not any(w.startswith("No nutrition data") for w in result.meta.warnings), name
    plate = await analyze(list(OWNER_MATCHES), jpeg_bytes, lookup)  # all together
    assert plate.totals.energy_kcal is not None and plate.totals.carbohydrate_g is not None
    expected = sum(
        item.nutrition.energy_kcal for item in plate.items if item.nutrition.energy_kcal is not None
    )
    assert plate.totals.energy_kcal == pytest.approx(expected)
    # a close/partial match carries a note about the approximation in the recogniser
    assert load_class_foods()["noodles"].is_approximate


@pytest.mark.skipif(not REAL_TABLE.is_file(), reason="the (gitignored) combined table is absent")
async def test_unmatched_classes_stay_null_with_the_warning(jpeg_bytes: bytes) -> None:
    lookup = CompositionTableLookup.from_csv(REAL_TABLE)
    for name in STAY_UNKNOWN:
        result = await analyze([name], jpeg_bytes, lookup)
        item = result.items[0]
        assert item.nutrition_source is None and item.nutrition.energy_kcal is None, name
        assert NO_NUTRITION_WARNING.format(label=name) in result.meta.warnings, name
    mixed = await analyze(["dhal_curry", "lunu_miris"], jpeg_bytes, lookup)
    assert mixed.items[0].nutrition.energy_kcal is not None
    assert mixed.totals.energy_kcal is None  # one unknown food makes the total unknown
