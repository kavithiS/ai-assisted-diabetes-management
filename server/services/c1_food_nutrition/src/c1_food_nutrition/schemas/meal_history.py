"""Schemas for the meal history and food search endpoints.

Demo data only. There is no image, no patient identifier and no model confidence here.
"""

from datetime import date, datetime
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from c1_food_nutrition.schemas.meal_analysis import MealType
from c1_food_nutrition.schemas.nutrition import NutrientProfile

MAX_ITEMS_PER_MEAL = 30
MAX_GRAMS = 5000.0


class MealItemIn(BaseModel):
    """One food to log: a stored food (``food_id``) or a free entry (``name`` + ``nutrients``)."""

    model_config = ConfigDict(extra="forbid")

    food_id: int | None = Field(
        default=None, ge=1, le=2_147_483_647, description="Id from GET /v1/foods."
    )
    name: str | None = Field(default=None, min_length=1, max_length=255)
    grams: float = Field(gt=0, le=MAX_GRAMS, description="Eaten amount in grams.")
    nutrients: NutrientProfile | None = Field(
        default=None,
        description="Nutrients of the whole portion (already scaled); only with ``name``.",
    )

    @model_validator(mode="after")
    def _one_way_to_describe_the_food(self) -> Self:
        if self.food_id is not None:
            if self.name is not None or self.nutrients is not None:
                raise ValueError("give either food_id, or name with optional nutrients, not both")
        elif self.name is None:
            raise ValueError("give food_id, or a name")
        return self


class MealCreate(BaseModel):
    """Request body of ``POST /v1/meals``."""

    model_config = ConfigDict(extra="forbid")

    eaten_at: AwareDatetime | None = Field(default=None, description="Defaults to now.")
    meal_type: MealType | None = None
    note: str | None = Field(default=None, max_length=255)
    items: list[MealItemIn] = Field(min_length=1, max_length=MAX_ITEMS_PER_MEAL)


class MealItemOut(BaseModel):
    """A logged food with the nutrients of the logged portion."""

    id: int
    food_id: int | None
    name: str
    grams: float
    nutrients: NutrientProfile


class MealOut(BaseModel):
    """A logged meal. A total is ``null`` when any item's value for it is unknown."""

    id: int
    eaten_at: datetime
    meal_type: MealType | None
    note: str | None
    items: list[MealItemOut]
    totals: NutrientProfile


class MealList(BaseModel):
    """Newest meals first."""

    meals: list[MealOut]


class DailySummary(BaseModel):
    """What was eaten on one day. A total is ``null`` when any logged value for it is unknown."""

    day: date
    meal_count: int
    totals: NutrientProfile
    meals: list[MealOut]


class FoodOut(BaseModel):
    """A food from the composition table, with per-100 g values."""

    id: int
    name: str
    name_si: str | None
    name_ta: str | None
    category: str | None
    source: str
    per_100g: NutrientProfile


class FoodList(BaseModel):
    """Search result."""

    foods: list[FoodOut]
