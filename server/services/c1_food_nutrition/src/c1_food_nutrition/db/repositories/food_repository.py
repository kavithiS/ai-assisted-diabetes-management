"""Data access for nutrition sources and foods."""

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from c1_food_nutrition.db.models import Food, FoodNutrient, NutritionSource
from c1_food_nutrition.schemas.nutrition import NUTRIENT_FIELDS


class FoodRepository:
    """CRUD operations for ``NutritionSource`` and ``Food`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_source(self, code: str) -> NutritionSource | None:
        """Return the source with ``code``, if present."""
        return self._session.scalar(select(NutritionSource).where(NutritionSource.code == code))

    def get_or_create_source(self, code: str, name: str) -> NutritionSource:
        """Return the source with ``code``, creating it if needed."""
        source = self.get_source(code)
        if source is None:
            source = NutritionSource(code=code, name=name)
            self._session.add(source)
            self._session.flush()
        return source

    def get_food(self, source_code: str, source_food_id: str) -> Food | None:
        """Return a food by its source and source-specific identifier."""
        return self._session.scalar(
            select(Food)
            .join(Food.source)
            .where(NutritionSource.code == source_code, Food.source_food_id == source_food_id)
        )

    def add_food(
        self,
        source: NutritionSource,
        *,
        source_food_id: str,
        name: str,
        nutrients_per_100g: Mapping[str, float],
        name_si: str | None = None,
        name_ta: str | None = None,
        category: str | None = None,
    ) -> Food:
        """Insert a food with its per-100 g nutrient values.

        Raises:
            ValueError: if a nutrient name is not one of ``NUTRIENT_FIELDS``.
        """
        unknown = set(nutrients_per_100g) - set(NUTRIENT_FIELDS)
        if unknown:
            raise ValueError(f"Unknown nutrient names: {sorted(unknown)}")
        food = Food(
            source=source,
            source_food_id=source_food_id,
            name=name,
            name_si=name_si,
            name_ta=name_ta,
            category=category,
            nutrients=[
                FoodNutrient(nutrient=nutrient, amount_per_100g=amount)
                for nutrient, amount in nutrients_per_100g.items()
            ],
        )
        self._session.add(food)
        self._session.flush()
        return food
