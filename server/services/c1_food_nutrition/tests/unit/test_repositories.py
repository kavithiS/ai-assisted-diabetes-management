"""Repository tests on in-memory SQLite. Every row here is a labelled TEST FIXTURE."""

from collections.abc import Iterator
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


@pytest.mark.parametrize("importer_type", [MriSriLankaImporter, UsdaFdcImporter])
def test_importer_stubs_are_not_implemented(
    importer_type: type[NutritionImporter], tmp_path: Path
) -> None:
    with pytest.raises(NotImplementedError):
        list(importer_type().parse(tmp_path))


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
