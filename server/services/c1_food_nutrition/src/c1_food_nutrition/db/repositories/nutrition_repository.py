"""Read access to nutrient values as ``NutrientProfile`` objects."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from c1_food_nutrition.db.models import Food, FoodNutrient, NutritionSource
from c1_food_nutrition.schemas.nutrition import NutrientProfile


class NutritionRepository:
    """Builds per-100 g nutrient profiles from stored composition data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_profile_per_100g(self, source_code: str, source_food_id: str) -> NutrientProfile | None:
        """Return the per-100 g profile of a food, or ``None`` if the food is unknown.

        Nutrients the source does not report are ``None`` in the profile.
        """
        food_id = self._session.scalar(
            select(Food.id)
            .join(Food.source)
            .where(NutritionSource.code == source_code, Food.source_food_id == source_food_id)
        )
        if food_id is None:
            return None
        rows = self._session.execute(
            select(FoodNutrient.nutrient, FoodNutrient.amount_per_100g).where(
                FoodNutrient.food_id == food_id
            )
        ).all()
        return NutrientProfile(**dict(rows))
