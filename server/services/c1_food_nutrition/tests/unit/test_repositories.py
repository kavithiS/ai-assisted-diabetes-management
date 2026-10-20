"""Repository tests on in-memory SQLite. Every row here is a labelled TEST FIXTURE."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import c1_food_nutrition.db.models  # noqa: F401
from c1_food_nutrition.db.base import Base
from c1_food_nutrition.db.importers.base import ImportedFood, NutritionImporter
from c1_food_nutrition.db.importers.mri_sri_lanka import MriSriLankaImporter
from c1_food_nutrition.db.importers.usda_fdc import UsdaFdcImporter
from c1_food_nutrition.db.repositories.food_repository import FoodRepository
from c1_food_nutrition.db.repositories.nutrition_repository import NutritionRepository
from c1_food_nutrition.db.session import create_db_engine, create_session_factory
from c1_food_nutrition.schemas.nutrition import NutritionSourceCode
from c1_food_nutrition.services.nutrition import CompositionTableError


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_db_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with create_session_factory(engine)() as session:
        yield session


def test_add_and_read_profile(session: Session) -> None:
    foods = FoodRepository(session)
    source = foods.get_or_create_source("FIXTURE_SOURCE", "Test fixture source")
    foods.add_food(
        source,
        source_food_id="FIXTURE-1",
        name="Fixture food",
        nutrients_per_100g={"energy_kcal": 123.0, "carbohydrate_g": 4.5},
    )
    session.commit()

    profile = NutritionRepository(session).get_profile_per_100g("FIXTURE_SOURCE", "FIXTURE-1")
    assert profile is not None
    assert profile.energy_kcal == 123.0
    assert profile.carbohydrate_g == 4.5
    assert profile.protein_g is None  # not reported -> unknown
    assert foods.get_or_create_source("FIXTURE_SOURCE", "ignored").id == source.id


def test_unknown_food_returns_none(session: Session) -> None:
    assert NutritionRepository(session).get_profile_per_100g("FIXTURE_SOURCE", "missing") is None


def test_unknown_nutrient_name_rejected(session: Session) -> None:
    foods = FoodRepository(session)
    source = foods.get_or_create_source("FIXTURE_SOURCE", "Test fixture source")
    with pytest.raises(ValueError, match="Unknown nutrient"):
        foods.add_food(source, source_food_id="F", name="F", nutrients_per_100g={"vitamin_q": 1})


def test_negative_amount_rejected_by_database(session: Session) -> None:
    foods = FoodRepository(session)
    source = foods.get_or_create_source("FIXTURE_SOURCE", "Test fixture source")
    with pytest.raises(IntegrityError):
        foods.add_food(source, source_food_id="F", name="F", nutrients_per_100g={"fat_g": -1.0})


def test_importers_read_only_their_own_source(
    session: Session, make_table: Callable[..., Path]
) -> None:
    table = make_table()
    foods = FoodRepository(session)
    assert MriSriLankaImporter().import_into(foods, table) == 3
    assert UsdaFdcImporter().import_into(foods, table) == 1
    session.commit()

    sl = foods.get_food("MRI_SL_FCDB", "SL_37")
    assert sl is not None
    assert {n.nutrient for n in sl.nutrients} == {  # fibre was blank, so it is not stored
        "energy_kcal",
        "carbohydrate_g",
        "protein_g",
        "fat_g",
        "sodium_mg",
    }
    zero = NutritionRepository(session).get_profile_per_100g("MRI_SL_FCDB", "SL_99")
    assert zero is not None
    assert zero.energy_kcal == 0.0  # a real zero stays zero
    assert foods.get_food("MRI_SL_FCDB", "BD_1") is None  # regional table is not allowed
    assert foods.get_food("USDA_FDC", "SL_9") is None


def test_importing_twice_updates_instead_of_duplicating(
    session: Session, make_table: Callable[..., Path]
) -> None:
    foods = FoodRepository(session)
    table = make_table()
    MriSriLankaImporter().import_into(foods, table)
    table.write_text(table.read_text().replace(",100,20,2,3,", ",111,20,2,3,"))
    MriSriLankaImporter().import_into(foods, table)
    session.commit()

    assert len(foods.search("Fixture", limit=50)) == 3
    profile = NutritionRepository(session).get_profile_per_100g("MRI_SL_FCDB", "SL_9")
    assert profile is not None
    assert profile.energy_kcal == 111.0


def test_importer_rejects_a_corrupted_header(
    session: Session, make_table: Callable[..., Path]
) -> None:
    bad = make_table(header="food_id,food_100me,source,energy_kcal", rows=())
    with pytest.raises(CompositionTableError):
        MriSriLankaImporter().import_into(FoodRepository(session), bad)


def test_import_into_persists_parsed_foods(session: Session, tmp_path: Path) -> None:
    class FixtureImporter(NutritionImporter):
        source_code = NutritionSourceCode.USDA_FDC
        source_name = "fixture importer"

        def parse(self, path: Path) -> Iterator[ImportedFood]:
            yield ImportedFood(
                source_food_id="FIXTURE-A", name="Fixture A", nutrients_per_100g={"protein_g": 1}
            )

    count = FixtureImporter().import_into(FoodRepository(session), tmp_path)
    assert count == 1
    assert FoodRepository(session).get_food("USDA_FDC", "FIXTURE-A") is not None
