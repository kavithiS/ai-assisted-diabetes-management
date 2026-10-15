"""Tests for the composition-table lookup. All table rows are TEST FIXTURES, not real data."""

from collections.abc import Callable
from pathlib import Path

import pytest

from c1_food_nutrition.ml.labels import load_class_foods
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode
from c1_food_nutrition.services.nutrition import CompositionTableError, CompositionTableLookup

TableFactory = Callable[..., Path]


def test_loads_only_allowed_sources(make_table: TableFactory) -> None:
    lookup = CompositionTableLookup.from_csv(make_table())
    assert len(lookup) == 4 and lookup.skipped_rows == 1  # the Bangladesh row is skipped
    assert lookup.is_mock is False
    assert lookup.per_100g("BD_1") is None
    sl = lookup.per_100g("SL_9")
    us = lookup.per_100g("US_1")
    assert sl is not None and us is not None
    assert sl[1].source is NutritionSourceCode.MRI_SL_FCDB and sl[1].source_food_id == "SL_9"
    assert us[1].source is NutritionSourceCode.USDA_FDC
    assert lookup.food_name("SL_9") == "Fixture Milk Rice"
    assert lookup.food_name("nope") is None and lookup.per_100g("nope") is None


def test_columns_map_to_contract_fields_and_blank_is_unknown(make_table: TableFactory) -> None:
    lookup = CompositionTableLookup.from_csv(make_table())
    milk = lookup.per_100g("SL_9")
    hoppers = lookup.per_100g("SL_37")
    assert milk is not None and hoppers is not None
    assert milk[0].model_dump() == {
        "energy_kcal": 100.0,
        "carbohydrate_g": 20.0,
        "sugars_g": None,  # the table has no sugars column
        "dietary_fiber_g": 1.0,
        "protein_g": 3.0,
        "fat_g": 2.0,
        "sodium_mg": 200.0,
    }
    assert hoppers[0].dietary_fiber_g is None  # blank cell: unknown, not zero


def test_a_real_zero_stays_zero(make_table: TableFactory) -> None:
    zero = CompositionTableLookup.from_csv(make_table()).per_100g("SL_99")
    assert zero is not None
    assert zero[0].energy_kcal == 0.0 and zero[0].carbohydrate_g == 0.0
    assert zero[0].sugars_g is None


def test_corrupted_header_is_rejected(make_table: TableFactory) -> None:
    bad = make_table(header="food_id,food_100me,source,energy_kcal", rows=())
    with pytest.raises(CompositionTableError, match="lacks columns"):
        CompositionTableLookup.from_csv(bad)


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("SL_1,A,x,,abc,1,1,1,1,1,Sri Lankan Food Composition Database,", "not a number"),
        ("SL_1,A,x,,-5,1,1,1,1,1,Sri Lankan Food Composition Database,", "0 or more"),
        ("SL_1,A,x,,nan,1,1,1,1,1,Sri Lankan Food Composition Database,", "0 or more"),
        (",A,x,,1,1,1,1,1,1,Sri Lankan Food Composition Database,", "empty or repeated"),
    ],
)
def test_bad_rows_name_the_file_and_row(make_table: TableFactory, row: str, message: str) -> None:
    path = make_table(rows=(row,))
    with pytest.raises(CompositionTableError, match=message) as info:
        CompositionTableLookup.from_csv(path)
    assert "table.csv" in str(info.value) and "row 2" in str(info.value)


def test_repeated_id_empty_table_and_missing_file(make_table: TableFactory, tmp_path: Path) -> None:
    row = "SL_1,A,x,,1,1,1,1,1,1,Sri Lankan Food Composition Database,"
    with pytest.raises(CompositionTableError, match="repeated"):
        CompositionTableLookup.from_csv(make_table(rows=(row, row)))
    only_regional = "BD_1,A,x,,1,1,1,1,1,1,Food Composition Table for Bangladesh (2013),"
    with pytest.raises(CompositionTableError, match="no rows from an allowed source"):
        CompositionTableLookup.from_csv(make_table(rows=(only_regional,)))
    with pytest.raises(CompositionTableError, match="cannot read"):
        CompositionTableLookup.from_csv(tmp_path / "missing.csv")


# ------------------------------------------- the shipped class map against the real table

REAL_TABLE = Path(__file__).parents[5] / "data" / "c1" / "c1_foods_combined.csv"


def test_every_matched_class_points_to_a_real_allowed_row() -> None:
    """Runs only where the (gitignored) combined table exists, i.e. on the owner's machine."""
    if not REAL_TABLE.is_file():
        pytest.skip(f"{REAL_TABLE} not present")
    lookup = CompositionTableLookup.from_csv(REAL_TABLE)
    matched = {name: e for name, e in load_class_foods().items() if e.food_id}
    assert len(matched) >= 31
    for name, entry in matched.items():
        found = lookup.per_100g(str(entry.food_id))
        assert found is not None, f"{name} -> {entry.food_id} is not an allowed table row"
        profile = found[0]
        assert profile.energy_kcal is not None and profile.carbohydrate_g is not None, name
        assert profile.protein_g is not None and profile.fat_g is not None, name
